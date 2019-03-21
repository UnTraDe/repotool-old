import os
import sys
import json
import requests

input_filename = None
output_filename = None
prepand_command = None
verbose = False
compare_file = None
filter_forks = False
only_forks = False

github_api_url_template = "https://api.github.com/{0}/{1}/repos?per_page=200" # &page=2

def write_urls(urls):
    global output_filename

    if output_filename is None:
        output_filename = "output.txt"

    filtered = []

    if compare_file is not None:
        archive = []
        with open(compare_file, "r") as f:
            archive = f.readlines()

        archive = [x.strip() for x in archive]

        for u in urls:
            if u not in archive:
                filtered.append(u)

    with open(output_filename, "w") as f:
        if len(filtered) == 0:
            final_urls = urls
        else:
            final_urls = filtered

        for url in final_urls:
            if prepand_command is not None:
                f.write(prepand_command.strip() + " " + url + "\n")
            else:
                f.write(url + "\n")
                
            if verbose:
                print('url "{0}" written'.format(url))
    
    print("written {0} repositories to {1} (skipped {2})".format(len(final_urls), output_filename, len(urls) - len(final_urls)))

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

def github_to_list(url):
    if verbose:
        print("GET " + url)
    
    r = requests.get(url)

    if r.status_code != 200:
        raise Exception("failed to get response code 200 from: " + url)

    repos = r.json()

    # if verbose:
    #     print("found {0} repositories".format(len(repos)))
    
    urls = []

    for repo in repos:
        if filter_forks and repo["fork"]:
            continue
        
        if only_forks and not repo["fork"]:            
            continue
            
        urls.append(repo["clone_url"])

    if "link" in r.headers:
        for l in r.headers["link"].split(','):
            entries = l.split(';')
            if entries[1].split('=')[1].replace('"', '') == "next":
                next_url = entries[0].replace('<', '').replace('>', '')
                print("found next page url: {0}".format(next_url))
                next_urls = github_to_list(next_url)
                urls.extend(next_urls)
                break

    return urls

def download_and_save_from_github(url):
    url_list = github_to_list(url)
    write_urls(url_list)

def print_help():
    pass

if __name__ == "__main__":
    arg_len = len(sys.argv)
    
    # print(sys.argv)

    cmd = None

    for i, arg in enumerate(sys.argv):
        if (arg == "-d" or arg == "--default") and i+1 <= arg_len:
            prepand_command = "git clone --mirror"
            output_filename = sys.argv[i+1] + ".txt"
            orgs_url = github_api_url_template.format("orgs", sys.argv[i+1])
            cmd = lambda: download_and_save_from_github(orgs_url)
        elif arg == "-i" and i+1 <= arg_len:
            input_filename = sys.argv[i+1]
        elif arg == "-o" and i+1 <= arg_len:
            output_filename = sys.argv[i+1]
        elif arg == "--m2url":
            cmd = modules_to_urls
        elif (arg == "-p" or arg == "--prepend") and i+1 <= arg_len:
            prepand_command = sys.argv[i+1]
        elif arg == "--github-orgs" and i+1 <= arg_len:
            orgs_url = github_api_url_template.format("orgs", sys.argv[i+1])
            cmd = lambda: download_and_save_from_github(orgs_url)
        elif arg == "--github-user" and i+1 <= arg_len:
            orgs_url = github_api_url_template.format("users", sys.argv[i+1])
            cmd = lambda: download_and_save_from_github(orgs_url)
        elif arg == "-v":
            verbose = True
        elif arg == "--scan-repos" and i+1 <= arg_len:
            reposdir = sys.argv[i+1]
            cmd = lambda: scan_reposdir(reposdir)
        elif arg == "--filter-forks" and i+1 <= arg_len:
            filter_forks = True
        elif arg == "--only-forks" and i+1 <= arg_len:
            only_forks = True
        elif arg == "-c" and i+1 <= arg_len:
            compare_file = sys.argv[i+1]

    if cmd is not None:
        cmd()
    else:
        print_help()
    
    print("done")
