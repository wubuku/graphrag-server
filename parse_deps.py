import tomli
import re

# Read pyproject.toml file
with open('/tmp/graphrag/pyproject.toml', 'rb') as f:
    data = tomli.load(f)

# Get dependencies list
deps = data['tool']['poetry']['dependencies']
excludes = {'spacy', 'python', 'graspologic', 'numpy'}  # Add numpy to exclusion list

# Convert version specifications
def convert_version(version_str):
    # Handle ^x.y.z format (convert to >=x.y.z,<(x+1).0.0)
    if version_str.startswith('^'):
        version = version_str.replace('^', '')
        major = version.split('.')[0]
        return f">={version},<{int(major)+1}.0.0"
    
    # Handle ~x.y.z format (convert to >=x.y.z,<x.(y+1).0)
    elif version_str.startswith('~'):
        version = version_str.replace('~', '')
        parts = version.split('.')
        if len(parts) >= 2:
            major, minor = parts[0], parts[1]
            return f">={version},<{major}.{int(minor)+1}.0"
        return f">={version}"
    
    # Keep other formats unchanged
    return version_str

# Write dependencies file
with open('/tmp/graphrag-deps.txt', 'w') as f:
    # Skip numpy explicit installation, already installed via conda
    
    # Add other dependencies, excluding specified packages
    for pkg, ver in deps.items():
        if pkg not in excludes:
            if isinstance(ver, dict):
                version = ver['version']
                version = convert_version(version)
                # Use == single version to avoid complex version ranges
                simple_version = version.replace(">=", "").replace("<", "").split(",")[0]
                f.write(f"{pkg}=={simple_version}\n")
            else:
                version = convert_version(ver)
                # Use == single version to avoid complex version ranges
                simple_version = version.replace(">=", "").replace("<", "").split(",")[0]
                f.write(f"{pkg}=={simple_version}\n")
    
    # Manually add special dependencies and version-conflicting dependencies
    f.write("fnllm[azure,openai]==0.2.3\n")
    f.write("graspologic==3.4.1\n")  # Use actually existing version

print("Dependencies parsing completed, saved to /tmp/graphrag-deps.txt")