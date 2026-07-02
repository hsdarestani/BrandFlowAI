PERMISSIONS={
 'super_admin':['*'], 'org_owner':['manage_org','manage_brand','publish','approve','analytics','billing'],
 'agency_admin':['manage_brand','publish','approve','analytics','invite'], 'brand_manager':['manage_brand','publish','approve','analytics'],
 'creator':['create_draft','edit_draft','request_approval'], 'client_approver':['approve','comment'], 'analyst':['analytics'], 'viewer':['read']}
def can(role, permission): return '*' in PERMISSIONS.get(role,[]) or permission in PERMISSIONS.get(role,[])
