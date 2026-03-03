import datetime
from fractions import Fraction
from caltib.api import get_calendar  # <-- Import it directly here!
from caltib.core.time import to_jdn, from_jdn

def run_diagnostic(target_date_str="2079-02-23"):
    print(f"--- Diagnostic for l2 around {target_date_str} ---")
    
    # 1. Load the engine
    eng = get_calendar("l2")  # <-- Call it directly
    
    # 2. Parse date and convert to continuous coordinates
    y, m, d = map(int, target_date_str.split("-"))
    target_date = datetime.date(y, m, d)
    
    jdn = to_jdn(target_date)
    t2000 = jdn - 2451545
    
    # 3. Get the absolute tithi index (x)
    x_base = eng.day.get_x_from_t2000(t2000)
    
    print(f"Target JDN: {jdn}")
    print(f"Base x (approximate): {x_base}")
    print("-" * 80)
    print(f"{'x (Tithi)':<12} | {'Continuous t2000':<18} | {'civil_jdn':<10} | {'Boundary Date':<15} | {'Width (Days)'}")
    print("-" * 80)
    
    # Get the starting boundary to calculate the first width
    prev_jdn = eng.day.civil_jdn(x_base - 6)
    
    for offset in range(-5, 6):
        x = x_base + offset
        
        # Query the exact physical boundaries
        t_cont = eng.day.local_civil_date(x)
        c_jdn = eng.day.civil_jdn(x)
        
        # Calculate how many dawns fell inside this tithi interval
        width = c_jdn - prev_jdn
        
        # Format the continuous time safely
        if isinstance(t_cont, Fraction):
            t_float = float(t_cont)
        else:
            t_float = float(t_cont)
            
        date_str = str(from_jdn(c_jdn))
        
        # Flag physical impossibilities
        flag = " <--- ERROR!" if width > 2 or width < 0 else ""
        
        print(f"{x:<12} | {t_float:<18.6f} | {c_jdn:<10} | {date_str:<15} | {width}{flag}")
        prev_jdn = c_jdn

if __name__ == "__main__":
    run_diagnostic()