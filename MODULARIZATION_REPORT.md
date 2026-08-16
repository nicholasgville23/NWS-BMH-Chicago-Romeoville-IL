import os

def generate_modularization_report(target_path, output_file="MODUCLARIZATION_REPORT.md"):
    report_content = f"# Modularization Report\n\n## Target Directory: `{target_path}`\n\n"

    for root, dirs, files in os.walk(target_path):
        level = root.replace(target_path, '').count(os.sep)
        indent = '  ' * (level)
        report_content += f"{indent}- **{os.path.basename(root) or 'Root'}/**\n"
        subindent = '  ' * (level + 1)
        for f in files:
            report_content += f"{subindent}- {f}\n"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_content)

target = r"C:\Users\nicho\Downloads\NWS-BMH-Chicago-Romeoville-IL-main\NWS-BMH-Chicago-Romeoville-IL-main\data\resources\runtime\WNG689"
generate_modularization_report(target)