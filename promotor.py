#! /usr/bin/env python3
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString
import argparse
import os
from sys import stdin, stderr, exit
import prettytable as pt
from datetime import datetime, UTC

DISTRIBUTION_TEMPLATE= """

I initiate a referendum on each of the following proposals, removing
them from the proposal pool. For each referendum the vote collector is the
Assessor, the quorum is {quorum}, the adoption index is that of the associated
proposal, the voting method is AI-majority, and the valid options are FOR
and AGAINST. (PRESENT and conditional votes are also both valid options.)

{distributions}

"""

MAIN_TEMPLATE = """
=================
PROMOTOR'S REPORT
=================
{distribution}
The proposal pool contains the following proposals (self-ratifying):
{pool}

Legend:
NNNN*: Democratic proposal
NNNN~: Ordinary proposal
NAME+: Coauthors listed below

The full text of all above mentioned proposal(s) is listed below. Where the information shown below differs from the information shown above, the information shown above shall control.
"""

EMPTY_REPORT = """
=================
PROMOTOR'S REPORT
=================

The proposal pool is empty.
"""

LISTING_TEMPLATE_POOL = """
==========
{name} (AI={ai})
author: {author}
coauthors: {coauthors}


{text}


"""

LISTING_TEMPLATE_DISTRIBUED = """
==========
{name} (AI={ai})
author: {author}
coauthors: {coauthors}


{text}


"""

yaml = YAML()

def first_missing(numbers: list[int]) -> int:
    for i in range(max(numbers)):
        if i not in numbers:
            return i
    return max(numbers) + 1

def highest_id() -> int:
    to_num = lambda x: lambda y: int(y[:-x])
    middle = str(max(map(to_num(3), os.listdir("proposals")))) + "xxx"
    proposal = max(map(to_num(4), os.listdir(os.path.join("proposals", middle))))
    return proposal

def add_proposal() -> None:
    name = input("Title: ")
    authors = input("authors (,-separated): ").split(",")
    adoption_index = float(input("AI: "))
    print("Text:")
    text = "".join(stdin.readlines())
    proposal = {
        "authors":  authors,
        "ai":       adoption_index,
        "name":     name,
        "text":     LiteralScalarString(text)
    }

    pool_numbers = list(map(lambda x: int(x[:-4]), os.listdir("pool")))
    new_number = first_missing(pool_numbers)

    fullpath = os.path.join("pool", str(new_number) + ".yml")
    with open(fullpath, "x") as f:
        yaml.dump(proposal, f)

def generate() -> str:
    distributions = pt.PrettyTable(
        ["ID", "Author", "AI", "Name"],
        hrules=pt.HRuleStyle.HEADER,
        vrules=pt.VRuleStyle.NONE,
        none_format=" ",
        align="l"
    )
    for key, value in {"ID":8, "Author":12, "AI":4, "Name":30}.items():     # I like fixed-width tables
        distributions.min_width[key] = value
        distributions.max_width[key] = value
    pool = distributions.copy()
    pool.del_column("ID")

    proposals = get_pool()
    for proposal in proposals:
        print(proposal["number"], proposal["name"])
    to_distribute, pool_proposals = select_proposals(proposals, input("Proposals to distribute: "))

    first_id = highest_id() + 1
    last_id = first_id + len(to_distribute) - 1
    distribution_range = f"{first_id}-{last_id}"

    for proposal, pid in zip(to_distribute, range(first_id, last_id + 1)):
        dest = open(os.path.join("proposals", str(pid)[:-3] + "xxx", f"{pid}.yml"), "x")
        srcpath = os.path.join("pool", f"{proposal["number"]}.yml")
        src = open(srcpath)
        data = yaml.load(src)
        data.insert(2, "id", str(pid))
        proposal["id"] = str(pid)
        yaml.dump(data, dest)
        src.close()
        dest.close()
        os.remove(srcpath)

    if not to_distribute:
        distributions.add_row([None, None, None, None]) # So the table has some space in between if it's empty
    else:
        distributions.add_rows(
            list([proposal["id"] + ("~" if proposal["ai"] < 3 else "*"),
             proposal["authors"][0] + ("+" if len(proposal["authors"]) > 1 else ""),
             proposal["ai"],
             proposal["name"]] for proposal in to_distribute)
        )
    distributions.add_divider()
    distributions.add_row([None, None, None, None]) # Jank so I get the bottom border as well
    if not pool_proposals:
        pool.add_row([None, None, None]) # So the table has some space in between if it's empty
    else:
        pool.add_rows(
            list([
             proposal["authors"][0] + ("+" if len(proposal["authors"]) > 1 else ""),
             proposal["ai"],
             proposal["name"]] for proposal in pool_proposals)
        )
    pool.add_divider()
    pool.add_row([None, None, None])

    formatted_distributions = "\n".join(line[2:] for line in distributions.get_string().splitlines()) # Get rid of the extra space at the start, it annoys me
    formatted_pool = "\n".join(line[2:] for line in pool.get_string().splitlines()) # Get rid of the extra space at the start, it annoys me

    # Table black magic done, now the rest
    quorum = input("Enter the quorum: ")
    distribution_text = DISTRIBUTION_TEMPLATE.format(quorum=quorum, distributions=formatted_distributions) if to_distribute else ""
    report = MAIN_TEMPLATE.format(distribution=distribution_text, pool=formatted_pool)
    for proposal in to_distribute:
        listing = LISTING_TEMPLATE_DISTRIBUED.format(
            id = proposal["id"],
            name = proposal["name"],
            ai = proposal["ai"],
            author = proposal["authors"][0],
            coauthors = ", ".join(proposal["authors"][1:]),
            text = proposal["text"]
        )
        report += listing
    for proposal in pool_proposals:
        listing = LISTING_TEMPLATE_POOL.format(
            name = proposal["name"],
            ai = proposal["ai"],
            author = proposal["authors"][0],
            coauthors = ", ".join(proposal["authors"][1:]),
            text = proposal["text"]
        )
        report += listing
    if not (to_distribute + pool_proposals):
        report = EMPTY_REPORT
    
    filename = (datetime.now(tz=UTC).strftime("%Y-%m-%d") + f" {distribution_range}").strip() + ".txt"
    with open(os.path.join("reports", filename), "xt") as f:
        f.write(report.removeprefix("\n"))
    return(report)




def get_pool() -> list[dict]:
    proposals = []
    filenames = os.listdir("pool")
    for name in filenames:
        fullpath = os.path.join("pool", name)
        with open(fullpath, "r") as f:
            proposal = yaml.load(f)
        proposal["number"] = int(name[:-4])
        proposals.append(proposal)
    return proposals
    
def select_proposals(pool: list[dict], selector: str, dist = None) -> tuple[list[dict], list[dict]]:
    if dist is None:
        dist = []
    if "," in selector:
        for newselector in selector.split(","):
            d, pool = select_proposals(pool, newselector)
            dist += d
    elif "-" in selector:
        start, end = selector.split("-")
        for i in range(int(start), int(end) + 1):
            d, pool = select_proposals(pool, str(i))
            dist += d
    else:
        d = -1
        for i, proposal in enumerate(pool):
            if proposal["number"] == int(selector):
                d = i
                break
        if d != -1:
            dist = [pool.pop(d)]
    return dist, pool
                


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["add", "a", "generate", "g"])
    args = parser.parse_args()

    if args.command in ["add", "a"]:
        add_proposal()
    elif args.command in ["generate", "g"]:
        print(generate())
 

if __name__ == "__main__":
    #main()
    generate()
    #main()
    generate()