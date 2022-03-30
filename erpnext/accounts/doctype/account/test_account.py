# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe

from erpnext.accounts.doctype.account.account import merge_account, update_account_number
from erpnext.stock import get_company_default_inventory_account, get_warehouse_account


class TestAccount(unittest.TestCase):
	def test_rename_account(self):
		if not frappe.db.exists("Account", "1210 - Debtors - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Debtors"
			acc.parent_account = "Accounts Receivable - _TC"
			acc.account_number = "1210"
			acc.company = "_Test Company"
			acc.insert()

		account_number, account_name = frappe.db.get_value(
			"Account", "1210 - Debtors - _TC", ["account_number", "account_name"]
		)
		self.assertEqual(account_number, "1210")
		self.assertEqual(account_name, "Debtors")

		new_account_number = "1211-11-4 - 6 - "
		new_account_name = "Debtors 1 - Test - "

		update_account_number("1210 - Debtors - _TC", new_account_name, new_account_number)

		new_acc = frappe.db.get_value(
			"Account",
			"1211-11-4 - 6 - - Debtors 1 - Test - - _TC",
			["account_name", "account_number"],
			as_dict=1,
		)

		self.assertEqual(new_acc.account_name, "Debtors 1 - Test -")
		self.assertEqual(new_acc.account_number, "1211-11-4 - 6 -")

		frappe.delete_doc("Account", "1211-11-4 - 6 - Debtors 1 - Test - - _TC")

	def test_merge_account(self):
		if not frappe.db.exists("Account", "Current Assets - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Current Assets"
			acc.is_group = 1
			acc.parent_account = "Application of Funds (Assets) - _TC"
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Securities and Deposits - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Securities and Deposits"
			acc.parent_account = "Current Assets - _TC"
			acc.is_group = 1
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Earnest Money - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Earnest Money"
			acc.parent_account = "Securities and Deposits - _TC"
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Cash In Hand - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Cash In Hand"
			acc.is_group = 1
			acc.parent_account = "Current Assets - _TC"
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Accumulated Depreciation - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Accumulated Depreciation"
			acc.parent_account = "Fixed Assets - _TC"
			acc.company = "_Test Company"
			acc.account_type = "Accumulated Depreciation"
			acc.insert()

		doc = frappe.get_doc("Account", "Securities and Deposits - _TC")
		parent = frappe.db.get_value("Account", "Earnest Money - _TC", "parent_account")

		self.assertEqual(parent, "Securities and Deposits - _TC")

		merge_account(
			"Securities and Deposits - _TC", "Cash In Hand - _TC", doc.is_group, doc.root_type, doc.company
		)
		parent = frappe.db.get_value("Account", "Earnest Money - _TC", "parent_account")

		# Parent account of the child account changes after merging
		self.assertEqual(parent, "Cash In Hand - _TC")

		# Old account doesn't exist after merging
		self.assertFalse(frappe.db.exists("Account", "Securities and Deposits - _TC"))

		doc = frappe.get_doc("Account", "Current Assets - _TC")

		# Raise error as is_group property doesn't match
		self.assertRaises(
			frappe.ValidationError,
			merge_account,
			"Current Assets - _TC",
			"Accumulated Depreciation - _TC",
			doc.is_group,
			doc.root_type,
			doc.company,
		)

		doc = frappe.get_doc("Account", "Capital Stock - _TC")

		# Raise error as root_type property doesn't match
		self.assertRaises(
			frappe.ValidationError,
			merge_account,
			"Capital Stock - _TC",
			"Softwares - _TC",
			doc.is_group,
			doc.root_type,
			doc.company,
		)

	def test_account_sync(self):
		frappe.local.flags.pop("ignore_root_company_validation", None)

		acc = frappe.new_doc("Account")
		acc.account_name = "Test Sync Account"
		acc.parent_account = "Temporary Accounts - _TC3"
		acc.company = "_Test Company 3"
		acc.insert()

		acc_tc_4 = frappe.db.get_value(
			"Account", {"account_name": "Test Sync Account", "company": "_Test Company 4"}
		)
		acc_tc_5 = frappe.db.get_value(
			"Account", {"account_name": "Test Sync Account", "company": "_Test Company 5"}
		)
		self.assertEqual(acc_tc_4, "Test Sync Account - _TC4")
		self.assertEqual(acc_tc_5, "Test Sync Account - _TC5")

	def test_add_account_to_a_group(self):
		frappe.db.set_value("Account", "Office Rent - _TC3", "is_group", 1)

		acc = frappe.new_doc("Account")
		acc.account_name = "Test Group Account"
		acc.parent_account = "Office Rent - _TC3"
		acc.company = "_Test Company 3"
		self.assertRaises(frappe.ValidationError, acc.insert)

		frappe.db.set_value("Account", "Office Rent - _TC3", "is_group", 0)

	def test_account_rename_sync(self):
		frappe.local.flags.pop("ignore_root_company_validation", None)

		acc = frappe.new_doc("Account")
		acc.account_name = "Test Rename Account"
		acc.parent_account = "Temporary Accounts - _TC3"
		acc.company = "_Test Company 3"
		acc.insert()

		# Rename account in parent company
		update_account_number(acc.name, "Test Rename Sync Account", "1234")

		# Check if renamed in children
		self.assertTrue(
			frappe.db.exists(
				"Account",
				{
					"account_name": "Test Rename Sync Account",
					"company": "_Test Company 4",
					"account_number": "1234",
				},
			)
		)
		self.assertTrue(
			frappe.db.exists(
				"Account",
				{
					"account_name": "Test Rename Sync Account",
					"company": "_Test Company 5",
					"account_number": "1234",
				},
			)
		)

		frappe.delete_doc("Account", "1234 - Test Rename Sync Account - _TC3")
		frappe.delete_doc("Account", "1234 - Test Rename Sync Account - _TC4")
		frappe.delete_doc("Account", "1234 - Test Rename Sync Account - _TC5")

	def test_child_company_account_rename_sync(self):
		frappe.local.flags.pop("ignore_root_company_validation", None)

		acc = frappe.new_doc("Account")
		acc.account_name = "Test Group Account"
		acc.parent_account = "Temporary Accounts - _TC3"
		acc.is_group = 1
		acc.company = "_Test Company 3"
		acc.insert()

		self.assertTrue(
			frappe.db.exists(
				"Account", {"account_name": "Test Group Account", "company": "_Test Company 4"}
			)
		)
		self.assertTrue(
			frappe.db.exists(
				"Account", {"account_name": "Test Group Account", "company": "_Test Company 5"}
			)
		)

		# Try renaming child company account
		acc_tc_5 = frappe.db.get_value(
			"Account", {"account_name": "Test Group Account", "company": "_Test Company 5"}
		)
		self.assertRaises(
			frappe.ValidationError, update_account_number, acc_tc_5, "Test Modified Account"
		)

		# Rename child company account with allow_account_creation_against_child_company enabled
		frappe.db.set_value(
			"Company", "_Test Company 5", "allow_account_creation_against_child_company", 1
		)

		update_account_number(acc_tc_5, "Test Modified Account")
		self.assertTrue(
			frappe.db.exists(
				"Account", {"name": "Test Modified Account - _TC5", "company": "_Test Company 5"}
			)
		)

		frappe.db.set_value(
			"Company", "_Test Company 5", "allow_account_creation_against_child_company", 0
		)

		to_delete = [
			"Test Group Account - _TC3",
			"Test Group Account - _TC4",
			"Test Modified Account - _TC5",
		]
		for doc in to_delete:
			frappe.delete_doc("Account", doc)

	def test_validate_account_currency(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		if not frappe.db.get_value("Account", "Test Currency Account - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Test Currency Account"
			acc.parent_account = "Tax Assets - _TC"
			acc.company = "_Test Company"
			acc.insert()
		else:
			acc = frappe.get_doc("Account", "Test Currency Account - _TC")

		self.assertEqual(acc.account_currency, "INR")

		# Make a JV against this account
		make_journal_entry(
			"Test Currency Account - _TC", "Miscellaneous Expenses - _TC", 100, submit=True
		)

		acc.account_currency = "USD"
		self.assertRaises(frappe.ValidationError, acc.save)


def get_inventory_account(company, warehouse=None):
	account = None
	if warehouse:
		account = get_warehouse_account(frappe.get_doc("Warehouse", warehouse))
	else:
		account = get_company_default_inventory_account(company)

	return account


def create_account(**kwargs):
	account = frappe.db.get_value(
		"Account", filters={"account_name": kwargs.get("account_name"), "company": kwargs.get("company")}
	)
	if account:
		return account
	else:
		account = frappe.get_doc(
			dict(
				doctype="Account",
				account_name=kwargs.get("account_name"),
				account_type=kwargs.get("account_type"),
				parent_account=kwargs.get("parent_account"),
				company=kwargs.get("company"),
				account_currency=kwargs.get("account_currency"),
			)
		)

		account.save()
		return account.name
