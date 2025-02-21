#!/usr/bin/python3
import os
import json
import hashlib

# Directory where your .crate and metadata JSON files are stored. Crates should be in {name}-{version}.crate, and metadata-v1 in {name}-{version}.json.
crate_directory = "downloads"

# Directory of the git repository for the crate index
index_directory = "index"

# Base URL of the (built) repository
base_url = os.environ.get('CI_PAGES_URL', "http://localhost:8080")


def compute_checksum(file_path):
    # This is just a sha256
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
    
def get_crate_index_path(crate_name, index_directory):
    """ Get the path in the index for a given crate name.
    https://doc.rust-lang.org/cargo/reference/registry-index.html#index-files
    """
    if len(crate_name) == 1:
        return os.path.join(index_directory, '1', crate_name)
    elif len(crate_name) == 2:
        return os.path.join(index_directory, '2', crate_name)
    elif len(crate_name) == 3:
        return os.path.join(index_directory, '3', crate_name[0], crate_name)
    else:
        return os.path.join(index_directory, crate_name[0:2], crate_name[2:4], crate_name)
        
def get_crate_data(crate_name, metadata):
    """ Get dependencies and features for a specific crate from the workspace metadata. """
    for package in metadata.get("packages", []):
        if package.get("name") == crate_name:
            return {
                "dependencies": package.get("dependencies", []),
                "features": package.get("features", {})
            }
    return {"dependencies": [], "features": {}}
    
def transform_dependencies(crate_dependencies, current_index_url):
    """ Transform dependencies from cargo metadata format to crate index format. """
    transformed_deps = []
    for dep in crate_dependencies:
        # Handle name and package based on presence of rename
        if dep.get("rename") is not None:
            dep_name = dep['rename']
        else:
            dep_name = dep['name']
        dep_package = dep["name"]

        # Handle registry transformation
        registry = dep.get("registry")
        if registry is None:
            registry = "https://github.com/rust-lang/crates.io-index"
        elif registry == current_index_url:
            registry = None

        transformed_dep = {
            "name": dep_name,
            "package": dep_package,
            "req": dep["req"],
            "features": dep.get("features", []),
            "optional": dep.get("optional", False),
            "default_features": dep.get("uses_default_features", True),
            "target": dep.get("target", None),
            "kind": dep.get("kind", "normal"),
            "registry": registry
        }
        transformed_deps.append(transformed_dep)
    return transformed_deps

# Make sure the index directory exists
os.makedirs(index_directory, exist_ok=True)

output_files = {}
for filename in os.listdir(crate_directory):
    if filename.endswith('.crate'):
        crate_name, crate_version = filename.rsplit('@', 1)[0], filename.rsplit('@')[-1][:-6]

        # Path to the metadata file
        metadata_path = os.path.join(crate_directory, f"{crate_name}@{crate_version}.json")

        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as metadata_file:
                metadata = json.load(metadata_file)
                
            metadata_extracted = get_crate_data(crate_name, metadata)
                
            cksum = compute_checksum(os.path.join(crate_directory, f"{crate_name}@{crate_version}.crate"))
            deps = transform_dependencies(metadata_extracted['dependencies'], 'http://localhost:3000/')

            # Define the necessary fields for the crate index
            crate_index_entry = {
                "name": crate_name,
                "vers": crate_version,
                "deps": deps,
                "cksum": cksum,
                "features": metadata_extracted.get("features", {}),
                "yanked": False,
                "links": None
            }

            
            output_filename = get_crate_index_path(crate_name, index_directory)
            output_files[output_filename] = output_files.get(output_filename, "") + json.dumps(crate_index_entry) + "\n"

# Config file
output_files[os.path.join(index_directory, 'config.json')] = json.dumps({"dl": base_url + "/" + crate_directory + "/{crate}@{version}.crate"})

# Write files
for filename, data in output_files.items():
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        f.write(data)

