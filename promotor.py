#! /usr/bin/env python3
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString
import argparse
import os
from sys import stdin, stderr, exit
import prettytable as pt
from datetime import datetime, UTC

MAIN_TEMPLATE = """
=================
PROMOTOR'S REPORT
=================

I initiate a referendum on each of the following proposals, removing
them from the proposal pool. For each referendum the vote collector is the
Assessor, the quorum is {quorum}, the adoption index is that of the associated
proposal, the voting method is AI-majority, and the valid options are FOR
and AGAINST. (PRESENT and conditional votes are also both valid options.)

{distributions}

The proposal pool contains the following proposals (self-ratifying):
{pool}

Legend:
NNNN*: Democratic proposal
NNNN~: Ordinary proposal
NAME+: Coauthors listed below

The full text of all above mentioned proposals is listed below.

"""

EMPTY_REPORT = """
=================
PROMOTOR'S REPORT
=================

The proposal pool is empty.
"""

LISTING_TEMPLATE = """
==========
ID {id}
{name} (AI={ai})
author: {author}
coauthors: {coauthors}


{text}


"""

yaml = YAML()

def add_proposal() -> None:
    proposal_id = input("ID: ")
    authors = input("authors (,-separated): ").split(",")
    adoption_index = float(input("AI: "))
    name = input("Name: ")
    print("Text:")
    text = "".join(stdin.readlines())
    proposal = {
        "id":       proposal_id,
        "authors":  authors,
        "ai":       adoption_index,
        "name":     name,
        "text":     LiteralScalarString(text)
    }

    outer = proposal_id[:-3] + "xxx"
    inner = proposal_id + ".json"
    fullpath = os.path.join("proposals", outer, inner)
    os.makedirs(os.path.dirname(fullpath), exist_ok=True)
    mode = "w" if os.path.exists(fullpath) else "x"
    with open(fullpath, mode) as f:
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
    distribution_range = input("Distribution range: ") 
    to_distribute = get_proposals(distribution_range)
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
    pool_range = input("Current pool (no input for empty pool): ")
    pool_proposals = get_proposals(pool_range)
    if not pool_proposals:
        pool.add_row([None, None, None, None]) # So the table has some space in between if it's empty
    else:
        pool.add_rows(
            list([proposal["id"] + ("~" if proposal["ai"] < 3 else "*"),
             proposal["authors"][0] + ("+" if len(proposal["authors"]) > 1 else ""),
             proposal["ai"],
             proposal["name"]] for proposal in pool_proposals)
        )
    pool.add_divider()
    pool.add_row([None, None, None, None])

    formatted_distributions = "\n".join(line[2:] for line in distributions.get_string().splitlines()) # Get rid of the extra space at the start, it annoys me
    formatted_pool = "\n".join(line[2:] for line in pool.get_string().splitlines()) # Get rid of the extra space at the start, it annoys me

    # Table black magic done, now the rest
    quorum = input("Enter the quorum: ")
    report = MAIN_TEMPLATE.format(quorum=quorum, distributions=formatted_distributions, pool=formatted_pool)
    for proposal in to_distribute + pool_proposals:
        listing = LISTING_TEMPLATE.format(
            id = proposal["id"],
            name = proposal["name"],
            ai = proposal["ai"],
            author = proposal["authors"][0],
            coauthors = ", ".join(proposal["authors"][1:]),
            text = proposal["text"]
        )
        report += listing
    if not (to_distribute + pool_proposals):
        report = EMPTY_REPORT
    
    filename = (datetime.now(tz=UTC).strftime("%Y-%m-%d") + f" {distribution_range},{pool_range}").strip(", ") + ".txt"
    with open(os.path.join("reports", filename), "xt") as f:
        f.write(report.removeprefix("\n"))
    return(report)




def get_proposals(input_ids: str) -> list[dict]:
    if not input_ids:
        return []
    if "-" not in input_ids:
        ids =  [input_ids]
    else:
        start, end = input_ids.split("-")
        ids = [str(i) for i in range(int(start), int(end) + 1)]
    proposals = []
    for proposal_id in ids:
        outer = proposal_id[:-3] + "xxx"
        middle = proposal_id[:-2] + "xx"
        inner = proposal_id + ".yml"
        fullpath = os.path.join("proposals", outer, middle, inner)
        if not os.path.exists(fullpath):
            print(f"ERROR: File does not exist: {os.path.abspath(fullpath)}", file=stderr)
            exit(1)
        with open(fullpath, "r") as f:
            proposal = yaml.load(f)
        proposals.append(proposal)
    return proposals
    

def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_argument("command", choices=["add", "a", "generate", "g"])
    args = parser.parse_args()

    if args.command in ["add", "a"]:
        add_proposal()
    elif args.command in ["generate", "g"]:
        print(generate())
    

if __name__ == "__main__":
    main()