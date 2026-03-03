from caltib.api import get_calendar

for eng_name in ["l1", "l4"]:
    eng = get_calendar(eng_name)
    try:
        # Check the amplitude of the first lunar term (Mp)
        term1 = eng.day.p.lunar_terms[0]
        amp_val = float(term1.amp)
        print(f"{eng_name} Term 1 (Mp) Amplitude: {amp_val:.6f} turns ({amp_val * 30:.2f} tithis)")
        
        # We don't need to redefine m0 here, just check the velocities
        b_elong = float(eng.day.p.B_elong)
        print(f"{eng_name} B_elong (Mean Velocity): {b_elong:.6f} turns/day")
    except Exception as e:
        print(f"{eng_name} missing parameters: {e}")