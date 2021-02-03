from functools import lru_cache
import os
import sys

import requests
import requests_cache
import re
from bs4 import BeautifulSoup

import time
import pickle

def check_if_raw_mat(material_name, itemLink=""):
    # check material to see if it can be broken down further

    if material_name in known_raw_materials:
        raw_mats_list.append(material_name)
        return

    if itemLink != "":
        wikiPage = requests.get(itemLink)
        soup = BeautifulSoup(wikiPage.content, "html.parser")
    else:
        searchQuery = (
            "https://subnautica.fandom.com/wiki/Special:Search?query=%s"
            % material_name.title().replace(" ", "+")
        )
        wikiSearch = requests.get(searchQuery)
        searchSoup = BeautifulSoup(wikiSearch.content, "html.parser")
        firstLink = searchSoup.find("a", attrs={"class": "unified-search__result__title"})["href"]
        page = requests.get(firstLink) 
        soup = BeautifulSoup(page.content, "html.parser")

    materialInfo = soup.find("aside")

    if "Raw Material" in materialInfo.text:
        known_raw_materials[material_name] = "Raw"
        raw_mats_list.append(material_name)
    elif "Large Resource Deposits" in materialInfo.text:
        known_raw_materials[material_name] = "Raw"
        raw_mats_list.append(material_name)
    else:
        getMaterialRecipe(material_name)


def getMaterialRecipe(material_name):

    # check if known recipe to save time
    if material_name in known_recipes:
        for item in known_recipes[material_name][0]:
            regex_match = re.search(" \(x[0-9]+", item)
            if regex_match is not None:
                new_item = item[: regex_match.start()]
                item_quantity = regex_match.group()[3:]
                for i in range(int(item_quantity)):
                    raw_mats_list.append(new_item)
            else:
                check_if_raw_mat(item)

        print('\t', end="")
        print(", ".join(known_recipes[material_name][0]), end=" -> ")
        print(", ".join(known_recipes[material_name][1]), end=" -> ")
        print(", ".join(known_recipes[material_name][2]))
        return 1

    # get item by searching wiki for its name
    search_query = (
        "https://subnautica.fandom.com/wiki/Special:Search?query=%s"
        % material_name.title().replace(" ", "+")
    )
    wiki_search = requests.get(search_query)
    search_soup = BeautifulSoup(wiki_search.content, "html.parser")
    try:
        first_link = search_soup.find("a", attrs={"class": "unified-search__result__title"})["href"]
    except TypeError:
        print("Item not found.")
        return 0
    page = requests.get(first_link) 
    soup = BeautifulSoup(page.content, "html.parser")

    # get material recipe
    material_recipe = soup.find("div", attrs={"style": "height:72px;"})

    try:
        recipe_item_spans = material_recipe.find_all("span")
    except:
        print("Item not found.")
        return 0

    arrow_pointer = 0
    first_arrow_index = 0
    second_arrow_index = 0
    recipe_items = []

    # get all titles of recipe links, keep track of arrows
    # in order to build an input -> station -> output
    for span in recipe_item_spans:

        span_class = span.get("class")

        item_child_link = span.findChild("a", recursive=False)
        arrow_class = ["image", "image-thumbnail"]

        if span_class == ["arrow-icon"]:
            # this is an arrow

            if first_arrow_index == 0:
                first_arrow_index = arrow_pointer
            else:
                second_arrow_index = arrow_pointer

        elif span_class == ["recipe-icon"]:
            # this is a material or output
            item_link = "https://subnautica.fandom.com%s" % item_child_link.get(
                "href"
            ).replace(" ", "")
            item_title = item_child_link.get("title")

            if second_arrow_index == 0:
                # this is not the output material, check if raw
                check_if_raw_mat(item_title, item_link)

        elif span_class == ["machine-icon"]:
            # this is a station
            item_title = item_child_link.get("title")

        elif span_class == ["inventory"] or span_class == ["times"]:
            # this is an item quantity
            inv_quantity = int(span.find("b").text)
            quantified_item_name = span.previous_sibling.findChild(
                "a", recursive=False
            ).get("title")
            if quantified_item_name not in raw_mats_dict:
                raw_mats_dict[quantified_item_name] = int(inv_quantity) - 1
            else:
                raw_mats_dict[quantified_item_name] += int(inv_quantity) - 1
            recipe_items[-1] += " (x%d)" % inv_quantity
            continue

        non_item_classes = ["inventory", "arrow-icon", "times"]
        if span_class not in non_item_classes:
            recipe_items.append(item_title)

        arrow_pointer += 1

    # split recipe up by materials -> station to put materials into -> output
    recipe_materials = recipe_items[:first_arrow_index]
    recipe_station = recipe_items[first_arrow_index + 1 : second_arrow_index]
    recipe_output = recipe_items[second_arrow_index + 1 :]

    known_recipes[material_name] = [recipe_materials, recipe_station, recipe_output]

    print("\t", end="")
    print(", ".join(recipe_materials), end=" -> ")
    print(recipe_station[0], end=" -> ")
    print(", ".join(recipe_output))

try:
    # cache every page grabbed
    requests_cache.install_cache("wikiCache")

    # also cache known raw materials and known recipes
    try:
        with open("knownRawMaterials.pickle", "rb") as known_raw_materials_handle:
            known_raw_materials = pickle.load(known_raw_materials_handle)
        with open("knownRecipes.pickle", "rb") as known_recipes_handle:
            known_recipes = pickle.load(known_recipes_handle)
    except:
        known_raw_materials = {}
        known_recipes = {}
        print("No cache found.")

    user_input = " "
    raw_mats_list = []
    raw_mats_dict = {}

    while user_input != "":
        user_input = input("Enter an item name.\n")
        start_time = time.time()
        status = getMaterialRecipe(user_input)
        if status == 1:
            # when finished, create frequency dictionary of raw materials and print
            for item in raw_mats_list:
                if item not in raw_mats_dict:
                    raw_mats_dict[item] = 1
                elif item in raw_mats_dict:
                    raw_mats_dict[item] += 1
            print('\n')
            for key, value in raw_mats_dict.items():
                print('\t', value, key)
            raw_mats_list = []
            raw_mats_dict = {}
            print("\n\ttime elapsed: {:.1f}s\n".format(time.time() - start_time))

            with open("knownRawMaterials.pickle", "wb") as known_raw_materials_handle:
                pickle.dump(
                    known_raw_materials, known_raw_materials_handle, protocol=pickle.HIGHEST_PROTOCOL
                )
            with open("knownRecipes.pickle", "wb") as known_recipes_handle:
                pickle.dump(known_recipes, known_recipes_handle, protocol=pickle.HIGHEST_PROTOCOL)
except KeyboardInterrupt:
    try:
        sys.exit(0)
    except:
        os._exit(0)
