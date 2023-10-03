import json
import os
import subprocess
import re

import requests

TOP_100 = "https://netsplit.de/networks/top100.php"

# Regex:
#       <td align="right" valign="top"><div class="minimum-tablet">95.</div></td><td align='center'><div class='minimum-tablet'></div></td>      <td align="left" style="word-break:break-all; word-break:break-word;" valign="top"><a href="/networks/Bondage.International/" title="Bondage.International IRC Network">Bondage.International</a></td>
# Find the number, and name (/networks/NAME/)

TOP_100_REGEX = re.compile(
    r"<div class=\"minimum-tablet\">(\d+)\.</div></td><td align='center'><div class='minimum-tablet'></div></td>      <td align=\"left\" style=\"word-break:break-all; word-break:break-word;\" valign=\"top\"><a href=\"/networks/([^\/]+)"
)
SERVER_REGEX = re.compile(r"a href='/servers/details\.php\?host=([^']+)")


def ipapicacheorget(ip):
    ret = {}
    print("getting info for", ip)
    if os.path.isfile(f"cache/{ip}.json"):
        with open(f"cache/{ip}.json") as f:
            return json.load(f)

    host = subprocess.run(["host", ip], capture_output=True, text=True)
    if "NXDOMAIN" in host.stdout:
        return {"_status": "error", "_message": "NXDOMAIN"}

    if int(host.returncode) != 0:
        return {"_status": "error", "_message": "host error"}

    if "has IPv6 address" in host.stdout and "has address" not in host.stdout:
        return {"_status": "error", "_message": "ipv6 only"}

    if host.stdout.count("has address") > 1:
        return {"_status": "error", "_message": "multiple IPv4s"}

    if os.system(f"ping -c 2 {ip} > /dev/null") != 0:
        ret = {"_status": "error", "_message": "not pingable"}
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
        if r.status_code != 200:
            return {"_status": "error", "_message": "ip-api error"}
    except:
        return {"_status": "error", "_message": "ip-api timeout"}
    with open(f"cache/{ip}.json", "w") as f:
        # add ret to the json
        ret.update(r.json())
        f.write(json.dumps(ret))
    return ret


INFO_CSV = "info.csv"


def main():
    # Get the top 100 list
    r = requests.get(
        TOP_100, headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}
    )
    # create info.csv if it doesn't exist
    if not os.path.isfile(INFO_CSV):
        with open(INFO_CSV, "w") as f:
            f.write("server,server_name_slug,network_name,country_code,as\n")
    # Find all the networks
    networks = TOP_100_REGEX.findall(r.text)

    # find servers now!
    SERVERS = "https://netsplit.de/servers/?net="
    for network_n, network_name in networks:
        print(f"Network #{network_n}: {network_name}")
        r = requests.get(
            SERVERS + network_name,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"},
        )
        servers = list(set(SERVER_REGEX.findall(r.text)))

        for server in servers:
            s_name = server
            # if already in info.csv, skip it
            if os.system(f"grep {server} {INFO_CSV} > /dev/null") == 0:
                print(f"    {server}: already in info.csv, skipping")
                continue
            # get some info from ip-api, cache it to file for later use
            info = ipapicacheorget(server)
            print("    ", info)
            if 'status' in info and info["status"] == "fail":
                print(f"    {server}: ip-api error, skipping")
                print(f"        {info['message']}")
                continue
            if (
                "_status" in info
                and info["_status"] != "success"
                and info["_message"] != "not pingable"
            ):
                print(f"    {server}: code error, skipping")
                print(f"        {info['_message']}")
                continue
            if (
                "_status" in info
                and info["_status"] == "error"
                and info["_message"] == "not pingable"
            ):
                print(f"    {server}: not pingable, adding with comment")
                s_name = f"#{server}"
            server_name_slug = "-".join(
                [network_name, server, info["countryCode"], info["as"].split()[0]]
            )
            # replace non- - characters with _
            server_name_slug = re.sub(r"[^a-zA-Z0-9\-]", "_", server_name_slug)
            print(f"    {server}: {server_name_slug}")

            # write to csv
            with open(INFO_CSV, "a") as f:
                f.write(
                    f"{s_name},{server_name_slug},{network_name},{info['countryCode']},{info['as']}\n"
                )


if __name__ == "__main__":
    main()
