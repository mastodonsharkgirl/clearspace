from pathlib import Path

CATEGORIES = ['Downloads to review', 'Personal media', 'Application managed', 'Development', 'Cloud / reparse', 'Protected / unknown']


def classify(m, protected=()):
    p = Path(m['path']); parts = {x.lower() for x in p.parts}
    if m.get('kind')=='error':
        return CATEGORIES[5], 'This location could not be measured. Access may be restricted or the item may have changed. Its contents and size remain unknown.', True, 'coverage'
    if m['cloud'] != 'ordinary-local' or m['reparse']:
        return CATEGORIES[4], 'Provider review only; content was not opened.', True, 'cloud'
    if any(p == Path(x) or Path(x) in p.parents for x in protected) or parts & {'windows', 'program files', 'program files (x86)', 'programdata', '$recycle.bin', 'system volume information'}:
        return CATEGORIES[5], 'Protected or system-owned location. Retain for owner review.', True, 'storage'
    if parts & {'appdata', 'packages', 'installer'} or p.suffix.lower() in {'.vhd', '.vhdx', '.db', '.sqlite', '.pst'}:
        return CATEGORIES[2], 'Review retention or uninstall through the owning application.', True, 'apps'
    if parts & {'.git', 'node_modules', '.venv', 'venv', 'target'}:
        return CATEGORIES[3], 'Project dependencies or source history. Check the project owner first.', True, 'review'
    if 'downloads' in parts:
        return CATEGORIES[0], 'Personal download candidate. Age and size do not establish that it is dispensable.', False, 'review'
    if p.suffix.lower() in {'.mp4', '.mov', '.jpg', '.png', '.wav', '.mp3'}:
        return CATEGORIES[1], 'Personal media. Verify backups and ownership before any manual change.', False, 'review'
    return CATEGORIES[5], 'Ownership or purpose is unknown. Keep for review.', True, 'review'


def validate_advice(suggestion, allowed):
    """Policy fixture only, not a model integration."""
    return suggestion if isinstance(suggestion, str) and suggestion in allowed else 'Unknown'
