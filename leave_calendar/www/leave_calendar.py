from datetime import date, datetime, timedelta
from enum import Enum

import frappe
from frappe.core.doctype.navbar_settings.navbar_settings import get_app_logo


class AttendenceCalendarDayType(Enum):
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"
    OFFICIAL_HOLIDAY = "Official Holiday"
    DEFAULT = "default"
    CASUAL_LEAVE = "casual_leave"
    SICK_LEAVE = "sick_leave"
    TRADE_SCHOOL = "trade_school"
    ABSENCE = "absence"
    HALF_DAY_CASUAL_LEAVE = "half_day_casual_leave"
    HALF_DAY_SICK_LEAVE = "half_day_sick_leave"
    HALF_DAY_TRADE_SCHOOL = "half_day_trade_school"
    HALF_DAY_ABSENCE = "half_day_absence"


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
        holiday for holiday in holidays if str(holiday["holiday_date"].year) == str(year)
    ]

    result = {}
    for holiday in filtered_holidays:
        holiday_type = get_type_of_day_for_holiday(holiday["description"])
        if holiday["parent"] not in result:
            result[holiday["parent"]] = {}
        result[holiday["parent"]][
            holiday["holiday_date"].strftime("%Y-%m-%d")
        ] = holiday_type

    return result


def get_type_of_day_for_holiday(description: str) -> AttendenceCalendarDayType:
    description = description.upper()
    if description in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]:
        return AttendenceCalendarDayType.ABSENCE
    elif description == "SATURDAY":
        return AttendenceCalendarDayType.SATURDAY
    elif description == "SUNDAY":
        return AttendenceCalendarDayType.SUNDAY
    else:
        return AttendenceCalendarDayType.OFFICIAL_HOLIDAY


def get_days_between(start_date, end_date):
    delta = end_date - start_date
    return [start_date + timedelta(days=i) for i in range(delta.days + 1)]


def map_leave_type(leave_type, half_day):
    if not leave_type:
        return (
            AttendenceCalendarDayType.ABSENCE
            if not half_day
            else AttendenceCalendarDayType.HALF_DAY_ABSENCE
        )

    leave_type = leave_type.upper()
    if leave_type == "CASUAL LEAVE":
        return (
            AttendenceCalendarDayType.CASUAL_LEAVE
            if not half_day
            else AttendenceCalendarDayType.HALF_DAY_CASUAL_LEAVE
        )
    elif leave_type == "SICK LEAVE":
        return (
            AttendenceCalendarDayType.SICK_LEAVE
            if not half_day
            else AttendenceCalendarDayType.HALF_DAY_SICK_LEAVE
        )
    elif leave_type == "TRADE SCHOOL":
        return (
            AttendenceCalendarDayType.TRADE_SCHOOL
            if not half_day
            else AttendenceCalendarDayType.HALF_DAY_TRADE_SCHOOL
        )
    else:
        return (
            AttendenceCalendarDayType.ABSENCE
            if not half_day
            else AttendenceCalendarDayType.HALF_DAY_ABSENCE
        )


def get_employees():
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "holiday_list", "department"],
    )
    return employees


def get_leave_allocations(year):
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    leave_allocations = frappe.get_all(
        "Leave Allocation",
        filters={
            "docstatus": ["!=", 2],
            "leave_type": "Casual Leave",
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
    days, holidays, year, is_admin, is_department_leave_approver, selected_department, current_employee
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
                days=days,
                holidays=holidays,
                is_admin=is_admin,
                is_department_leave_approver=is_department_leave_approver,
                current_employee=current_employee,
                )
        )

    return employee_data


def map_single_employee_data(
    employee,
    leave_allocation,
    leave_applications,
    days,
    holidays,
    is_admin,
    is_department_leave_approver,
    current_employee,
):
    employee_data = {}
    employee_days = []
    used_days = 0

    employee_data["employee_name"] = employee.employee_name

    is_department_leave_approver_accessible = (
        current_employee and
        (employee.name == current_employee.name
        or employee.department == current_employee.department)
    )

    can_see_leave_data = (
        is_admin
        or (is_department_leave_approver and is_department_leave_approver_accessible)
        or (current_employee and employee.name == current_employee.name)
    )


    employee_holiday_list = employee.holiday_list
    for day in days:
        day_type = AttendenceCalendarDayType.DEFAULT
        day_str = day.strftime("%Y-%m-%d")
        if (
            employee_holiday_list in holidays
            and day_str in holidays[employee_holiday_list]
        ):
            day_type = holidays[employee_holiday_list][day_str]

        elif day_str in leave_applications:
            leave_type = leave_applications[day_str]["type"]
            half_day = leave_applications[day_str]["half_day"]
            day_type = map_leave_type(leave_type, half_day)
            if day_type == AttendenceCalendarDayType.CASUAL_LEAVE:
                used_days += 1
            elif day_type == AttendenceCalendarDayType.HALF_DAY_CASUAL_LEAVE:
                used_days += 0.5

            if not can_see_leave_data:
                day_type = map_restricted_leave(day_type)

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
    employee_data["used_leaves"] = format_number(used_days if can_see_leave_data else "-")

    return employee_data


def get_leave_value(leave_allocation, can_see_leave_data, leave_allocation_key):
    if not can_see_leave_data:
        return "-"
    return leave_allocation.get(leave_allocation_key, 0) if leave_allocation else 0


def format_number(number):
    if isinstance(number, float) and number.is_integer():
        number = int(number)

    return number


def get_departments():
    departments = frappe.get_all("Department", filters={"disabled": 0, "is_group": 0}, fields=["name"])
    return departments


def map_restricted_leave(result_type):
    if result_type == AttendenceCalendarDayType.CASUAL_LEAVE:
        return AttendenceCalendarDayType.ABSENCE
    elif result_type == AttendenceCalendarDayType.HALF_DAY_CASUAL_LEAVE:
        return AttendenceCalendarDayType.HALF_DAY_ABSENCE
    elif result_type == AttendenceCalendarDayType.SICK_LEAVE:
        return AttendenceCalendarDayType.ABSENCE
    elif result_type == AttendenceCalendarDayType.HALF_DAY_SICK_LEAVE:
        return AttendenceCalendarDayType.HALF_DAY_ABSENCE
    else:
        return result_type


def check_if_logged_in():
    if frappe.session.user != "Guest":
        return True
    else:
        return False


def check_user_role(*roles):
    user_roles = frappe.get_roles(frappe.session.user)
    return any(role in user_roles for role in roles)


def get_current_employee(user):
    employees = frappe.get_all("Employee", filters={"user_id": user}, fields=["name", "department"])
    if employees:
        return employees[0]
    else:
        return None


def get_context(context):
    	
    context.no_cache = 1
    context.logged_in = check_if_logged_in()
    is_admin = False
    is_department_leave_approver = False

    if context.logged_in:
        is_admin = check_user_role("System Manager")
        #TODO: check 
        is_department_leave_approver = False

    context.departments = get_departments()
    current_year = datetime.now().year
    year = int(frappe.local.request.args.get("year", current_year))
    context.year = year
    context.current_date = datetime.now().strftime("%d.%m.")

    days = get_days_for_year(year)
    holidays = get_holidays_list(year)
    context.day_headers = format_days_to_dd_mm(days)

    selected_department = frappe.local.request.args.get("department", "all")
    context.selected_department = selected_department

    current_employee = get_current_employee(frappe.session.user)

    context.employee_data = map_employee_data(
        days=days,
        holidays=holidays,
        year=year,
        is_admin=is_admin,
        is_department_leave_approver=is_department_leave_approver,
        selected_department=selected_department,
        current_employee=current_employee,
    )
    context.logo = frappe.utils.get_url() + get_app_logo()
    context.favicon = frappe.utils.get_url() + "/assets/erpnext/images/erpnext-logo.svg"
    
    return context
