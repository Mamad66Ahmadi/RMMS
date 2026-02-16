# Select_options_function

def get_department_options():
    """
    Returns the list of allowed department options.
    """
    return [
        "CBM",
        "Electrical",
        "Fix",
        "Inspection",
        "Instrument",
        "Method",
        "Process",
        "Rotary",
        "Service S",
        "Utility",
        "Maintenance",
        "HSE",
        "HVAC"
    ]

def get_status_options():
    return [
        "Completed",
        "Ongoing",
        "On Hold"
    ]

def get_performed_job_options():
    return [
        "Check (Inspection)",
        "Repair",
        "Change",
        "Service",
        "Fabrication",
        "scaffolding",
        "Install/Remove (Spade/Despade)",
        "Oil Change"
    ]