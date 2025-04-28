from datetime import date, datetime, timedelta

import frappe
from frappe.core.doctype.navbar_settings.navbar_settings import get_app_logo


class LeaveType:
    def __init__(self, name, color, abbreviation, is_main_leave_type, half_day):
        self.name = name
        self.color = color
        self.abbreviation = abbreviation
        self.is_main_leave_type = is_main_leave_type
        self.half_day = half_day


def get_days_for_year(year):
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)

    all_days = []
    current_date = start_date

    while current_date <= end_date:
        all_days.append(current_date)
        current_date += timedelta(days=1)

    return all_days


def format_days_to_dd_mm(days):
    return [day.strftime("%d.%m.") for day in days]


def get_holidays_list(year):
    holidays = frappe.get_all(
        "Holiday",
        filters={"docstatus": ["!=", 2]},
        fields=["parent", "holiday_date", "description"],
    )

    filtered_holidays = [
        holiday
        for holiday in holidays
        if str(holiday["holiday_date"].year) == str(year)
    ]

    result = {}
    for holiday in filtered_holidays:
        holiday_type = get_type_of_day_for_holiday(holiday["description"])
        if holiday["parent"] not in result:
            result[holiday["parent"]] = {}
        result[holiday["parent"]][holiday["holiday_date"].strftime("%Y-%m-%d")] = (
            holiday_type
        )

    return result


def get_type_of_day_for_holiday(description: str):
    description = description.upper()
    if description in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]:
        return "ABSENCE"
    elif description == "SATURDAY":
        return "SATURDAY"
    elif description == "SUNDAY":
        return "SUNDAY"
    else:
        return "OFFICIAL HOLIDAY"


def get_days_between(start_date, end_date):
    delta = end_date - start_date
    return [start_date + timedelta(days=i) for i in range(delta.days + 1)]


def get_employees():
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=[
            "name",
            "employee_name",
            "holiday_list",
            "department",
            "leave_approver",
        ],
    )
    return employees


def get_leave_allocations(year):
    main_leave_type = frappe.get_all(
        "Leave Type Child Table",
        filters={"parent": "Leave Calendar Settings", "is_main_leave_type": 1},
        fields=["leave_type"],
    )
    if not main_leave_type:
        return []

    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    leave_allocations = frappe.get_all(
        "Leave Allocation",
        filters={
            "docstatus": ["!=", 2],
            "leave_type": main_leave_type[0].leave_type,
            "from_date": ["between", [start_date, end_date]],
        },
        fields=["*"],
    )

    return leave_allocations


def get_leave_applications(year):
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    leave_applications = frappe.get_all(
        "Leave Application",
        filters={"docstatus": ["!=", 2], "status": "Approved"},
        or_filters=[
            ["from_date", "between", [start_date, end_date]],
            ["to_date", "between", [start_date, end_date]],
        ],
        fields=[
            "from_date",
            "to_date",
            "employee",
            "leave_type",
            "half_day",
            "half_day_date",
        ],
    )

    return leave_applications


def map_employee_data(
    days, holidays, year, is_admin, selected_department, current_employee
):
    employee_data = []
    unsorted_employees = get_employees()
    if not unsorted_employees:
        return employee_data

    employees = sorted(unsorted_employees, key=lambda employee: employee.employee_name)

    if selected_department != "all":
        employees = [
            employee
            for employee in employees
            if employee.department == selected_department
        ]

    leave_allocations = get_leave_allocations(year)
    leave_applications = get_leave_applications(year)

    current_user = frappe.session.user

    for employee in employees:
        employee_leave_allocation = next(
            (
                allocation
                for allocation in leave_allocations
                if allocation.employee == employee.name
            ),
            None,
        )
        employee_leave_applications = [
            application
            for application in leave_applications
            if application.employee == employee.name
        ]

        employee_leave_application_array = {}

        for leave_application in employee_leave_applications:
            from_date = (
                leave_application.from_date
                if isinstance(leave_application.from_date, (datetime | date))
                else datetime.strptime(leave_application.from_date, "%Y-%m-%d")
            )
            to_date = (
                leave_application.to_date
                if isinstance(leave_application.to_date, (datetime | date))
                else datetime.strptime(leave_application.to_date, "%Y-%m-%d")
            )
            for day in get_days_between(from_date, to_date):
                formatted_day = day.strftime("%Y-%m-%d")
                employee_leave_application_array[formatted_day] = {
                    "type": leave_application.leave_type,
                    "half_day": (
                        leave_application.half_day == 1
                        and leave_application.half_day_date.strftime("%Y-%m-%d")
                        == formatted_day
                    ),
                }

        employee_data.append(
            map_single_employee_data(
                employee=employee,
                leave_allocation=employee_leave_allocation,
                leave_applications=employee_leave_application_array,
                selected_department=selected_department,
                days=days,
                holidays=holidays,
                is_admin=is_admin,
                current_employee=current_employee,
                current_user=current_user,
            )
        )

    return employee_data


def map_single_employee_data(
    employee,
    leave_allocation,
    leave_applications,
    selected_department,
    days,
    holidays,
    is_admin,
    current_employee,
    current_user,
):
    employee_data = {}
    employee_days = []
    used_days = 0

    employee_data["employee_name"] = employee.employee_name

    is_department_leave_approver = check_if_leave_approver(
        selected_department, employee, current_user
    )

    can_see_leave_data = (
        is_admin
        or (is_department_leave_approver)
        or (current_employee and employee.name == current_employee.name)
    )

    employee_holiday_list = employee.holiday_list
    if not employee_holiday_list:
        company_holiday_list = frappe.db.get_value(
            "Company", employee.company, "default_holiday_list"
        )
        if company_holiday_list:
            employee_holiday_list = company_holiday_list

    leave_types = get_leave_types()
    for day in days:
        day_str = day.strftime("%Y-%m-%d")

        day_type = LeaveType(
            name="DEFAULT",
            color="#636363",
            abbreviation="",
            is_main_leave_type=0,
            half_day=0,
        )

        if (
            employee_holiday_list in holidays
            and day_str in holidays[employee_holiday_list]
        ):
            day_type = map_leave_type(
                leave_type=holidays[employee_holiday_list][day_str],
                half_day=0,
                leave_types=leave_types,
                can_see_leave_data=1,
            )

        elif day_str in leave_applications:
            leave_type = leave_applications[day_str]["type"]
            half_day = leave_applications[day_str]["half_day"]
            day_type = map_leave_type(
                leave_type=leave_type,
                half_day=half_day,
                leave_types=leave_types,
                can_see_leave_data=can_see_leave_data,
            )

            if day_type.is_main_leave_type:
                used_days += 0.5 if day_type.half_day else 1

        employee_days.append({"type": day_type})

    employee_data["days"] = employee_days

    employee_data["total_leaves_allocated"] = format_number(
        get_leave_value(leave_allocation, can_see_leave_data, "total_leaves_allocated")
    )
    employee_data["new_leaves_allocated"] = format_number(
        get_leave_value(leave_allocation, can_see_leave_data, "new_leaves_allocated")
    )
    employee_data["unused_leaves"] = format_number(
        get_leave_value(leave_allocation, can_see_leave_data, "unused_leaves")
    )

    total_leaves = format_number(
        leave_allocation.get("total_leaves_allocated", 0) if leave_allocation else 0
    )
    used_leaves = format_number(used_days)

    employee_data["used_leaves"] = used_leaves if can_see_leave_data else "-"
    employee_data["remaining_leaves"] = (
        (total_leaves - used_leaves) if can_see_leave_data else "-"
    )

    return employee_data


def map_leave_type(leave_type, half_day, leave_types, can_see_leave_data):
    day_type_mapping = {
        "ABSENCE": {"color": "#ca3f3f", "abbreviation": "A"},
        "SATURDAY": {"color": "#636363", "abbreviation": "S"},
        "SUNDAY": {"color": "#636363", "abbreviation": "S"},
        "OFFICIAL HOLIDAY": {"color": "#78ca79", "abbreviation": "H"},
    }

    day_type = LeaveType(
        name="ABSENCE",
        color=day_type_mapping["ABSENCE"]["color"],
        abbreviation=day_type_mapping["ABSENCE"]["abbreviation"],
        is_main_leave_type=0,
        half_day=half_day,
    )

    if leave_type in day_type_mapping:
        day_type.name = leave_type
        day_type.color = day_type_mapping[day_type.name]["color"]
        day_type.abbreviation = day_type_mapping[day_type.name]["abbreviation"]

    else:
        if can_see_leave_data:
            for leave in leave_types:
                if leave.leave_type == leave_type:
                    day_type.name = leave_type.upper()
                    day_type.color = leave.color
                    day_type.abbreviation = leave.abbreviation
                    day_type.is_main_leave_type = leave.is_main_leave_type

    return day_type


def get_leave_value(leave_allocation, can_see_leave_data, leave_allocation_key):
    if not can_see_leave_data:
        return "-"
    return leave_allocation.get(leave_allocation_key, 0) if leave_allocation else 0


def format_number(number):
    if isinstance(number, float) and number.is_integer():
        number = int(number)

    return number


def check_if_leave_approver(department, employee, current_user):
    is_approver = False
    department_name = department if department != "all" else employee.department
    department_doc = None

    if department_name:
        department_doc = frappe.get_doc("Department", department_name)

    if employee.leave_approver == current_user:
        is_approver = True
        return is_approver

    if department_doc:
        for leave_approver in department_doc.leave_approvers:
            if leave_approver.approver == current_user:
                is_approver = True
                break

    return is_approver


def get_departments():
    departments = frappe.get_all(
        "Department", filters={"disabled": 0, "is_group": 0}, fields=["name"]
    )
    return departments


def get_leave_types():
    leave_types = frappe.get_all(
        "Leave Type Child Table",
        filters={"parent": "Leave Calendar Settings"},
        fields=["leave_type", "color", "abbreviation", "is_main_leave_type"],
    )
    return leave_types


def check_if_logged_in():
    if frappe.session.user != "Guest":
        return True
    else:
        return False


def check_user_role(*roles):
    user_roles = frappe.get_roles(frappe.session.user)
    return any(role in user_roles for role in roles)


def get_current_employee(user):
    employees = frappe.get_all(
        "Employee", filters={"user_id": user}, fields=["name", "department"]
    )
    if employees:
        return employees[0]
    else:
        return None


def get_context(context):
    context.no_cache = 1
    context.logged_in = check_if_logged_in()
    is_admin = False

    if context.logged_in:
        is_admin = check_user_role("System Manager")

    selected_department = frappe.local.request.args.get("department", "all")
    context.selected_department = selected_department

    context.leave_types = get_leave_types()
    context.departments = get_departments()
    current_year = datetime.now().year
    year = int(frappe.local.request.args.get("year", current_year))
    context.year = year
    context.current_date = datetime.now().strftime("%d.%m.")

    days = get_days_for_year(year)
    holidays = get_holidays_list(year)
    context.day_headers = format_days_to_dd_mm(days)

    current_employee = get_current_employee(frappe.session.user)

    context.employee_data = map_employee_data(
        days=days,
        holidays=holidays,
        year=year,
        is_admin=is_admin,
        selected_department=selected_department,
        current_employee=current_employee,
    )
    context.logo = frappe.utils.get_url() + get_app_logo()
    context.favicon = frappe.utils.get_url() + "/assets/erpnext/images/erpnext-logo.svg"

    return context
