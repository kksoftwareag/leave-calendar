# Copyright (c) 2025, K&K Software AG and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe import _
import frappe

class LeaveCalendarSettings(Document):
	def validate(self):
		checked_rows = [leave_type for leave_type in self.leave_types if leave_type.is_main_leave_type]

		if len(checked_rows) > 1:
			frappe.throw(_("Only one Leave Type can be Main Leave Type"))