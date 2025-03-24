#!/usr/bin/python3
import os
import sys 
import json
import argparse

from packaging.specifiers import SpecifierSet
from packaging.version import Version

REGISTRY_PRIVATE = 'sparse+https://rust.gitlab-pages.protontech.ch/shared/registry/index/'
REGISTRY_PUBLIC  = 'sparse+https://rust.gitlab-pages.protontech.ch/shared/public-registry/index/'

def parse_cargo_requirement(requirement: str) -> str:
    """
    Convert Cargo-style version requirements to semver-compatible ones.
    """
    def default_requirement(requirement, caret=True):
        if caret:
            requirement = requirement[1:]
        # ^1.2.3 means >=1.2.3, <2.0.0
        version = [ int(x) for x in requirement.split('.')]
        if version[0] > 0:
            return f">={requirement},<{version[0] + 1}.0.0"
        else:
            return f">={requirement},<{version[0]}.{version[1] + 1}.0"
            
    if requirement.startswith('^'):
        return default_requirement(requirement, caret=True)
    elif requirement.startswith('~'):
        # ~1.2.3 means >=1.2.3, <1.3.0
        requirement = requirement[1:]
        version = requirement.split('.')
        return f">={requirement},<{version[0]}.{version[1] + 1}.0"
    else:
        return default_requirement(requirement, caret=False)

def assert_package_in_registry(name, version, download_content, version_as_req=False):
    '''Assert that the package `name` with `version` is in the registry.
    If version_as_req is True, the version is a requirement and we try to check that we have a compatible version    
    '''
    if name not in download_content:
        raise RuntimeError(f"Can not find {name} in registry")

    if version_as_req: 
        requirement = SpecifierSet(*version.split(','))  # Your requirement
        
        versions = download_content[name]

        # Check if any version matches
        matches = any(requirement.contains(version) for version in versions)
        
        if not matches: 
            raise RuntimeError(f"Can not find a compatible version with {name}={requirement} in registry")
    elif Version(version) not in download_content[name]:
        raise RuntimeError(f"Can not find {name}={version} in registry")


def rewrite_reg_if_possible(dep, download_content):
    '''format of dep must be %registry%#%name%@%version%'''
    (registry, name_version) = dep.split('#')
    package = split_name_version(name_version)
    
    if registry != REGISTRY_PRIVATE:
        return dep

    assert_package_in_registry(package['name'], package['version'], download_content)
    return dep.replace(REGISTRY_PRIVATE, REGISTRY_PUBLIC)

def split_name_version(name_version):
    '''split %package_name%@%version% in a dict { %package_name% : %version% }'''
    return dict(zip(('name', 'version'), name_version.rsplit('@')))
    
def merge_package(package_list):
    '''merge a list ({ %package_name% : %version% }) into a single dictionary { %package_name% : [%version1%, %version2%, ...] }'''
    merged_list = {}

    for package in package_list:
        if 'version' in package:
            merged_list.setdefault(package['name'], []).append(Version(package['version']))

    return merged_list

parser = argparse.ArgumentParser(description="Check dependencies")
parser.add_argument("--check-only", action="store_true", help="Only check do not rewrite", default=True)
parser.add_argument("--name-version", type=str, required=True, help="Specify name-version (e.g., muon-impl-0.13.1)")

args = parser.parse_args()

name_dash_version = args.name_version

name, version = name_dash_version.rsplit('-', 1)
metadata_file_path = f"downloads/{name}@{version}.json"

# read the download directory and build a dictionary mapping package to all known versions
download_content = os.listdir("downloads/")
download_content = [split_name_version(os.path.splitext(file)[0]) for file in download_content if file.endswith('.crate')]
download_content = merge_package(download_content)

# read the metadata file (json)
with open(metadata_file_path, 'r') as meta:
    meta = json.load(meta)

# rewrite packages
for package in meta['packages']:
    
    package['id'] = rewrite_reg_if_possible(package['id'], download_content)

    if package['source'] == REGISTRY_PRIVATE:
        package['source'] = REGISTRY_PUBLIC # we asserted already 

    for dependency in package['dependencies']:
        name = dependency['name']
        registry = dependency['registry']
        source = dependency['source']
        req = dependency['req']

        if registry == REGISTRY_PRIVATE or source == REGISTRY_PRIVATE:
            # check if we have a satisfying version
            parsed_req = parse_cargo_requirement(req)

            assert_package_in_registry(name, parsed_req, download_content, version_as_req=True)

            if registry == REGISTRY_PRIVATE: 
                dependency['registry'] = REGISTRY_PUBLIC

            if source == REGISTRY_PRIVATE: 
                dependency['source'] = REGISTRY_PUBLIC

# rewrite dependency graph
for node in meta['resolve']['nodes']:
    # rewrite id to point to the public registry
    node['id'] = rewrite_reg_if_possible(node['id'], download_content)
    # rewrite all dependencies
    node['dependencies'] = [rewrite_reg_if_possible(dep, download_content) for dep in node['dependencies']]
    # rewrite deps
    for dep in node['deps']:
        dep['pkg'] = rewrite_reg_if_possible(dep['pkg'], download_content)

# rewrite the metadata file (json)
if not args.check_only:
    with open(metadata_file_path, 'w') as f:
        json.dump(meta, f)

sys.exit(0)



