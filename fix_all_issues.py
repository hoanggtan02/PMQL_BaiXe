import sys

with open("src/pmql/ui/app.py", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Replace list_by_branch with list_active
content = content.replace(
    "await l_repo.list_by_branch(settings.branch_id)",
    "await l_repo.list_active()"
)

# Fix 2: Add "settings" to page_factories dict
old_factories = '"accounts": self.accounts_page}'
new_factories = '"accounts": self.accounts_page, "settings": self.settings_page}'
content = content.replace(old_factories, new_factories)

# Fix 3: Add "Cài đặt" to sidebar nav groups
old_sidebar = '(\"HỆ THỐNG\", [(\"accounts\", \"♙  Tài khoản & phân quyền\")])'
new_sidebar = '(\"HỆ THỐNG\", [(\"accounts\", \"♙  Tài khoản & phân quyền\"), (\"settings\", \"⚙  Cài đặt\")])'
content = content.replace(old_sidebar, new_sidebar)

# Fix 4: Add "settings" to breadcrumb map in go()
old_go = '"accounts":"Tài khoản & phân quyền"}'
new_go = '"accounts":"Tài khoản & phân quyền", "settings":"Cài đặt hệ thống"}'
content = content.replace(old_go, new_go)

# Fix 5: Make sidebar scrollable when window shrinks — add ScrollArea around sidebar content
# The sidebar has fixed width 250, we need to make nav buttons shrink text or sidebar be in scroll area
# Simple fix: reduce sidebar min width and allow text wrapping via setWordWrap/setMinimumWidth
old_sidebar_fixed = "side.setFixedWidth(250)"
new_sidebar_fixed = "side.setFixedWidth(220)"
content = content.replace(old_sidebar_fixed, new_sidebar_fixed)

with open("src/pmql/ui/app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixes applied:")
print("1. list_by_branch -> list_active")
print("2. settings added to page_factories")
print("3. Cai dat added to sidebar")
print("4. Breadcrumb updated for settings")
