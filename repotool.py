import os
import sys
import json
import requests

input_filename = None
output_filename = None
prepand_command = None
verbose = False

github_orgs_url_template = "https://api.github.com/orgs/{0}/repos?per_page=200"

def write_urls(urls):
    global output_filename

    if output_filename is None:
        output_filename = "output.txt"

    with open(output_filename, "w") as f:
        for url in urls:
            if prepand_command is not None:
                f.write(prepand_command.strip() + " " + url + "\n")
            else:
                f.write(url + "\n")
                
            if verbose:
                print('url "{0}" written'.format(url))

    print("written {0} repositories to {1}".format(len(urls), output_filename))

def find_git_dir(path):
    with os.scandir(path) as it:
        for entry in it:            
            if entry.is_dir() and entry.name == ".git":
                return entry.path
    return None

def find_config(path):
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file() and entry.name == "config":
                return entry.path
    return None

def get_url(path):
    with open(path, "r") as f:
        for line in f:
            pair = line.replace(" ", "").replace("\t", "").replace("\n", "").split("=")
            if len(pair) is not 2:
                continue
            if pair[0] == "url":
                return pair[1]
    return None

def scan_reposdir(reposdir, level=0, urls=[]):
    with os.scandir(reposdir) as it:
        for entry in it:
            if entry.is_dir():
                git_dir = find_git_dir(entry.path)

                if git_dir is None:
                    git_dir = entry.path
                    
                conf_file = find_config(git_dir)

                if conf_file is not None:      
                    url = get_url(conf_file)

                    if url is not None:
                        urls.append(url)
                elif level < 1:
                    scan_reposdir(git_dir, level+1, urls)

    if level == 0:
        write_urls(urls)

def modules_to_urls():
    if input_filename is None:
        raise Exception("missing input filename")
    
    urls = []

    with open(input_filename, "r") as f:
        for line in f:
            url = line.replace("\n", "").replace(" ", "").replace("\t", "")
            parts = url.split("=")

            if len(parts) == 2 and parts[0] == "url":
                urls.append(parts[1])

    write_urls(urls)

def github_orgs_to_list(github_org_url):
    if verbose:
        print("GET " + github_org_url)
    
    r = requests.get(github_org_url)

    if r.status_code != 200:
        raise Exception("failed to get response code 200 from: " + github_org_url)
    
    repos = r.json()

    if verbose:
        print("found {0} repositories".format(len(repos)))

    urls = []

    for repo in repos:
        urls.append(repo["clone_url"])

    write_urls(urls)

def print_help():
    pass

if __name__ == "__main__":
    arg_len = len(sys.argv)

    # print(sys.argv)

    cmd = None

    for i, arg in enumerate(sys.argv):
        if arg == "-i" and i+1 <= arg_len:
            input_filename = sys.argv[i+1]
        elif arg == "-o" and i+1 <= arg_len:
            output_filename = sys.argv[i+1]
        elif arg == "--m2url":
            cmd = modules_to_urls
        elif (arg == "-p" or arg == "--prepend") and i+1 <= arg_len:
            prepand_command = sys.argv[i+1]
        elif arg == "--github-orgs" and i+1 <= arg_len:
            orgs_url = github_orgs_url_template.format(sys.argv[i+1])
            cmd = lambda: github_orgs_to_list(orgs_url)
        elif arg == "-v":
            verbose = True
        elif arg == "--scan-repos" and i+1 <= arg_len:
            reposdir = sys.argv[i+1]
            cmd = lambda: scan_reposdir(reposdir)

    if cmd is not None:
        cmd()
    else:
        print_help()
    
    print("done")