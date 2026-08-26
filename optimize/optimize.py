import numpy as np
import os
import subprocess, shutil, tempfile
import sys
import time

opath = sys.argv[1]
seed_offset = sys.argv[2]

BASE="/sdf/data/atlas/u/jkrupa/hepemshow/hepemshow/"
opath = BASE + "/build/hepemshow_utils/optimize" + opath +"/seed_offset"+seed_offset
print("Output path:", opath)
if os.path.exists(opath):
  print("Output path already exists, exiting.")
  sys.exit(1)
os.makedirs(opath)

# Common simulation flags (regularizations + stop-grad)
SIM_FLAGS = [
    "--stop-grad-mode", "2",
    "-y", "1",
    "-f", "0.05",
    "-k", "-1.",
    "-B", "1",
    "-N", "1e-3",
    "-C", "1000",
]

beam_energies = [25000]
absorber_thicknesses = [5.0]
n_max_epochs = 300
n_epochs=200
nevents_per_proc = 200
nprocs = 25
use_adam = False
lr_decay = True
increase_clipping_with_patience = True
num_decays = 0
max_decays = 3

# per-coordinate base rates
lr = np.array([1.0,    0.1e-6])    # [for energy, for thickness]

# Early stopping: stop if loss does not improve (relative) for N epochs
early_stop_patience = 30
early_stop_min_rel_improve = 1e-7
best_loss = np.inf
stalled_epochs = 0

### ADAM OPTIMIZER ###
# Adam hyper-params
b1, b2 = 0.9, 0.999
eps    = 1e-8
# state init
m = np.zeros(2)
v = np.zeros(2)
######################

### GRAD CLIPPING ###
use_grad_clipping = True
x_pct = 0.2      # e.g. 5% of the energy range per step
y_pct = 0.2      # e.g. 5% of the thickness range per step
E_min, E_max   = 5000.0, 25000.0
a_min, a_max   =    1.0,     3.5
E_range    = E_max - E_min   # 20000
a_range    = a_max - a_min   # 2.5
# compute absolute clip sizes once
max_step_a = 1. #mm
max_step_E = 2000. #MeV
#####################


#NOMSC TARGET EDEPS
#target_edeps = np.array([  4.81290754,   8.81070495,  15.83789511,  26.01777636,  39.41235027,  55.95764301,  75.41034907,  97.33970329, 121.1534089 , 146.14773484, 171.55870179, 196.61880587, 220.60719586, 242.88692102, 262.93978917, 280.36998316, 294.91720813, 306.44258062, 314.92310149, 320.43441526, 323.12351794, 323.1989709 , 320.90868274, 316.52417314, 310.32481902, 302.58635916, 293.57977812, 283.55819867, 272.75286424, 261.37447311, 249.61142073, 237.6283872 , 225.5704447 , 213.5554617 , 201.68531503, 190.04571781, 178.70574356, 167.71530179, 157.1197539 , 146.94676517, 137.21806276, 127.94465937, 119.13002612, 110.77172242, 102.8620772 ,  95.38106966,  88.29969749,  81.56518079,  75.05166679,  68.22225278])

#MSC TARGET EDEPS
target_edeps = np.array([  6.44720956,  11.79173741,  20.02149913,  31.95206159,
        47.9909972 ,  66.91844529,  89.41778528, 113.90719478,
       140.82566728, 168.820834  , 195.85531888, 219.99708905,
       243.70740818, 268.87485451, 287.30212994, 302.01039517,
       316.04630012, 327.02940627, 334.06695477, 337.75965538,
       336.72465625, 333.73688956, 329.14702084, 323.78267712,
       314.71196688, 307.11630178, 294.93432329, 281.11202882,
       267.87407676, 255.33010566, 241.88277465, 229.58843553,
       216.80904855, 201.9387832 , 189.50195292, 174.88187943,
       164.32877834, 153.95496684, 141.50670561, 131.93556534,
       122.27717228, 113.81493825, 104.92110335,  98.25718919,
        89.15019442,  82.73998634,  76.57967363,  69.18894586,
        64.13626066,  54.4685019 ])


print("Running with settings:"
      f"\n use_adam={use_adam}"
      f"\n lr_decay={lr_decay}"
      f"\n initial lr={lr}"
      f"\n grad_clipping={use_grad_clipping} (max steps: E={max_step_E} MeV, a={max_step_a} mm)"
      f"\n increase_clipping_with_patience={increase_clipping_with_patience}"
      f"\n early_stop: patience={early_stop_patience}, min_rel_improve={early_stop_min_rel_improve}"
      f"\n nprocs={nprocs}, nevents_per_proc={nevents_per_proc}"
      f"\n target_edeps={target_edeps}"
      f"\n output path={opath}"
      f"\n seed_offset={seed_offset}"
      f"\n max epochs={n_max_epochs}"
      )

for i in range(0,n_epochs):
  t = i+1
  beam_energy = beam_energies[-1]
  absorber_thickness = absorber_thicknesses[-1]
  print(str(i).rjust(3), str(beam_energy).rjust(20), str(absorber_thickness).rjust(20))
  seed = int(seed_offset) * (n_max_epochs * nprocs * 2) + i * (nprocs * 2)
  print("Using seed:", seed)

  # Forward run: Determine how much the present edep distribution deviates from the target edep distribution
  t0 = time.time()
  tmpdir = tempfile.mkdtemp(prefix=f"opt_fwd_{seed}_")
  forward_runs = []
  fwd_cwds = []

  for iproc in range(nprocs):
    proc_dir = os.path.join(tmpdir, str(iproc))
    os.makedirs(proc_dir)
    fwd_cwds.append(proc_dir)
    proc = subprocess.Popen([f"{BASE}/build/HepEmShow",
                             "-d", f"{BASE}/data/hepem_data.json",
                             "-n", str(nevents_per_proc),
                             "-e", str(beam_energy),
                             "-a", str(absorber_thickness),
                             "-s", str(seed+iproc)] + SIM_FLAGS,
                             cwd=proc_dir,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             )
    forward_runs.append(proc)

  edeps = np.zeros(50, dtype=np.float64)
  n_fwd_ok = 0
  for iproc in range(nprocs):
    try:
        retcode = forward_runs[iproc].wait()
        if retcode != 0:
            print(f"[Warning] forward_runs[{iproc}] exited with return code {retcode}")
            continue
        edeps += np.loadtxt(os.path.join(fwd_cwds[iproc], f"edeps_{seed+iproc}"))[:,0]
        n_fwd_ok += 1
    except Exception as e:
      print(f"[warning] forward mode failure while waiting for process {iproc}: {e!r}")
  shutil.rmtree(tmpdir)
  print(f"[time] forward pass: {time.time()-t0:.1f}s  ({n_fwd_ok}/{nprocs} ok)")
  if n_fwd_ok == 0:
    print(f"[ERROR] All forward procs failed at epoch {i}, skipping.")
    continue
  edeps /= n_fwd_ok
  print("edeps now = ", edeps)
  loss = float(np.mean((edeps - target_edeps) ** 2))
  print(f"loss = {loss:.6e} (best={best_loss:.6e}, stalled={stalled_epochs})")

  bar_edeps = 2*(edeps-target_edeps) #gradient
  # Reverse run: Back-propagate bar_edeps to parameters
  t0 = time.time()
  tmpdir = tempfile.mkdtemp(prefix=f"opt_rev_{seed}_")
  reverse_runs = []
  rev_cwds = []
  for iproc in range(nprocs):
    proc_dir = os.path.join(tmpdir, str(iproc))
    os.makedirs(proc_dir)
    rev_cwds.append(proc_dir)
    proc = subprocess.Popen([f"{BASE}/build_reverse/HepEmShow",
                             "-d", f"{BASE}/data/hepem_data.json",
                             "-n", str(nevents_per_proc),
                             "-e", str(beam_energy),
                             "-a", str(absorber_thickness),
                             "-s", str(seed+nprocs+iproc),
                             "-b", ":".join([str(bar_edep) for bar_edep in bar_edeps])] + SIM_FLAGS,
                             cwd=proc_dir,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             )
    reverse_runs.append(proc)

  bar_inputs = np.zeros(2, dtype=np.float64)
  n_rev_ok = 0
  for iproc in range(nprocs):
      try:
          retcode = reverse_runs[iproc].wait()
          if retcode != 0:
              print(f"[Warning] reverse_runs[{iproc}] exited with return code {retcode}")
              continue
      except Exception as e:
          print(f"[Error] Exception while waiting for process {iproc}: {e!r}")
          continue
      try:
          this_bar = np.loadtxt(os.path.join(rev_cwds[iproc], "barInputs"))[[2,0], 0]
          bar_inputs += this_bar
          n_rev_ok += 1
      except Exception as e:
          print(f"[Warning] Could not load barInputs for proc-{iproc}: {e!r}")
          continue
  shutil.rmtree(tmpdir)
  print(f"[time] reverse pass: {time.time()-t0:.1f}s  ({n_rev_ok}/{nprocs} ok)")
  if n_rev_ok == 0:
    print(f"[ERROR] All reverse procs failed at epoch {i}, skipping.")
    continue
  bar_inputs /= n_rev_ok
  if use_grad_clipping:
    max_grad_E = max_step_E / lr[0]
    max_grad_a = max_step_a / lr[1]
    orig_bar_input_E =  bar_inputs[0]
    orig_bar_input_a =  bar_inputs[1]
    # now clip the step to your “trust region”
    bar_inputs[0] = np.clip(bar_inputs[0], -max_grad_E, max_grad_E)
    bar_inputs[1] = np.clip(bar_inputs[1], -max_grad_a, max_grad_a)
    # report if clipping happened
    if bar_inputs[0] != orig_bar_input_E:
        print(f"[clip] energy bar_input clipped from {orig_bar_input_E:.3f} to {bar_inputs[0]:.3f}")
    if bar_inputs[1] != orig_bar_input_a:
        print(f"[clip] thickness bar_input clipped from {orig_bar_input_a:.3e} to {bar_inputs[1]:.3e}")

  if use_adam: #ADAM
    m = b1*m + (1-b1)*bar_inputs
    v = b2*v + (1-b2)*(bar_inputs**2)

    # 2) bias-correct
    m_hat = m / (1 - b1**t)
    v_hat = v / (1 - b2**t)

    # 3) compute Adam step *per coordinate*
    step = lr * (m_hat / (np.sqrt(v_hat) + eps))
  else: #Plain SGD
    step = lr * bar_inputs     # lr is your [1.0, 0.1e-6] vector

  print("steps: ", step)
  beam_energy        -= step[0]
  absorber_thickness -= step[1]
  if absorber_thickness < 0.01:
    absorber_thickness = 0.01
  if beam_energy < 1:
    beam_energy = 1.

  #if (new_absorber_thickness) < 0.01:
  #  new_absorber_thickness= 0.01
  beam_energies.append( beam_energy )
  absorber_thicknesses.append( absorber_thickness )
  np.savez(f"{opath}/epoch_{i:04d}.npz",
           bar_edeps=bar_edeps,
           edeps=edeps,
           target_edeps=target_edeps,
           bar_inputs=bar_inputs,
           beam_energy=beam_energy,
           absorber_thickness=absorber_thickness,
           loss=loss,
           best_loss=best_loss,
           stalled_epochs=stalled_epochs,
  )

  if loss < best_loss * (1 - early_stop_min_rel_improve):
    best_loss = loss
    stalled_epochs = 0
  else:
    stalled_epochs += 1

  if lr_decay and (stalled_epochs >= early_stop_patience):
    lr *= 0.5
    stalled_epochs = 0
    num_decays += 1
    if increase_clipping_with_patience:
        max_step_E *= 0.5
        max_step_a *= 0.5
        print(f"Increasing grad clipping to max steps: E={max_step_E} MeV, a={max_step_a} mm")
    print(f"Reducing LR to {lr}")
    if num_decays >= max_decays:
        break
  elif stalled_epochs >= early_stop_patience:
    print(f"[early-stop] No relative improvement > {early_stop_min_rel_improve:.1e} for {early_stop_patience} epochs; stopping at epoch {i}.")
    break


