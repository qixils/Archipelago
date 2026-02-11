from BaseClasses import CollectionState
from worlds.generic.Rules import exclusion_rules

from Options import ExcludeLocations
from .Options import CombatDifficulty, DeathLink, HardAdvancements, StructureCompasses

from rule_builder.options import OptionFilter
from rule_builder.rules import Has, CanReachRegion

from . import Constants
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import MinecraftWorld


def set_all_rules(self: "MinecraftWorld") -> None:
    set_main_rules(self)
    set_special_rules(self)


def set_main_rules(self: "MinecraftWorld") -> None:
    # new_world = self.get_entrance("New World")
    nether_portal = self.get_entrance("Nether Portal")
    end_portal = self.get_entrance("End Portal")
    overworld_structure_1 = self.get_entrance("Overworld Structure 1")
    overworld_structure_2 = self.get_entrance("Overworld Structure 2")
    nether_structure_1 = self.get_entrance("Nether Structure 1")
    nether_structure_2 = self.get_entrance("Nether Structure 2")
    the_end_structure = self.get_entrance("The End Structure")
    ocean = self.get_entrance("Ocean")
    dark_forest = self.get_entrance("Dark Forest")
    deep_dark = self.get_entrance("Deep Dark")
    ruins = self.get_entrance("Ruins")
    underground = self.get_entrance("Underground")

    nether = CanReachRegion("The Nether")
    the_end = CanReachRegion("The End")
    village = CanReachRegion("Village")
    outpost = CanReachRegion("Pillager Outpost")
    fortress = CanReachRegion("Nether Fortress")
    bastion = CanReachRegion("Bastion Remnant")
    end_city = CanReachRegion("End City")
    monument = CanReachRegion("Ocean Monument")
    mansion = CanReachRegion("Woodland Mansion")
    ancient_city = CanReachRegion("Ancient City")
    trail_ruins = CanReachRegion("Trail Ruins")
    trial_chambers = CanReachRegion("Trial Chambers")

    stone_tools = Has("Progressive Tools")
    furnace = Has("Progressive Resource Crafting")
    iron_ingots = stone_tools & furnace
    copper_ingots = iron_ingots

    iron_tools = Has("Progressive Tools", count=2) & iron_ingots
    diamond_tools = Has("Progressive Tools", count=3) & iron_ingots

    stone_weapons = Has("Progressive Weapons")
    iron_weapons = Has("Progressive Weapons", count=2) & iron_ingots
    diamond_weapons = Has("Progressive Weapons", count=3) & iron_tools

    iron_armor = Has("Progressive Armor") & iron_ingots
    diamond_armor = Has("Progressive Armor", count=2) & iron_tools

    bow = Has("Archery")
    resource_blocks = Has("Progressive Resource Crafting", count=2)
    crossbow = bow & iron_ingots
    blaze_rods = Has("Blaze Rods")
    brewing = Has("Brewing") & blaze_rods
    can_enchant = Has("Enchanting") & diamond_tools
    anvil = Has("Enchanting") & resource_blocks & iron_ingots
    enchanted_books = can_enchant & anvil
    bucket = Has("Bucket") & iron_ingots
    flint_and_steel = Has("Flint and Steel") & iron_ingots
    bed = Has("Bed")
    bottles = Has("Bottles") & furnace
    potions = brewing & bottles
    shield = Has("Shield") & iron_ingots
    fishing_rod = Has("Fishing Rod")
    campfire = Has("Campfire")
    netherite_scrap = Has("8 Netherite Scrap")
    channeling = Has("Channeling Book") & enchanted_books
    silk_touch = Has("Silk Touch Book") & enchanted_books
    piercing_iv = Has("Piercing IV Book") & enchanted_books
    ender_pearls = Has("3 Ender Pearls")
    saddle = Has("Saddle") & iron_ingots
    brush = Has("Brush") & copper_ingots

    gold_ingots = iron_tools | nether & Has("Progressive Resource Crafting")
    ancient_debris = potions & bed & diamond_tools
    eye_of_ender = ender_pearls & brewing

    piglin_bartering = gold_ingots & (nether | bastion)

    cure_zombie = potions & gold_ingots

    village_dimension = self.get_region("Village").entrances[0].parent_region.name

    if village_dimension == "The Nether":
        overworld_villagers = cure_zombie | (village & diamond_tools)
    elif village_dimension == "The End":
        overworld_villagers = cure_zombie
    else:
        overworld_villagers = village | cure_zombie

    no_death_link = OptionFilter(DeathLink, False)
    death_link_check = no_death_link | bed

    easy = OptionFilter(CombatDifficulty, CombatDifficulty.option_easy)
    normal = OptionFilter(CombatDifficulty, CombatDifficulty.option_normal)
    hard = OptionFilter(CombatDifficulty, CombatDifficulty.option_hard)

    easy_adventure = easy & iron_weapons & death_link_check
    normal_adventure = normal & stone_weapons & (furnace | campfire) & death_link_check
    can_adventure = easy_adventure | normal_adventure | hard

    spyglass = Has("Spyglass") & copper_ingots & can_adventure
    lead = Has("Lead") & can_adventure
    stronghold = eye_of_ender & can_adventure

    easy_combat = easy & iron_weapons & iron_armor & shield
    normal_combat = normal & stone_weapons & (iron_armor | shield)
    combat = easy_combat | normal_combat | hard

    loot_fortress = fortress & combat
    enchanted_golden_apple = iron_tools & combat & bastion

    easy_ominous_vaults = easy & diamond_weapons & diamond_armor & shield
    normal_ominous_vaults = normal & iron_weapons & iron_armor & shield
    hard_ominous_vaults = hard & iron_weapons & (iron_armor | shield)
    ominous_vaults = trial_chambers & outpost & (easy_ominous_vaults | normal_ominous_vaults | hard_ominous_vaults)

    hard_advancements = OptionFilter(HardAdvancements, True)
    exclude_mace = [OptionFilter(ExcludeLocations, ExcludeLocations("Over-Overkill"))]
    mace = ominous_vaults & hard_advancements & exclude_mace

    easy_raid = easy & diamond_weapons & diamond_armor & shield & bow
    normal_raid = normal & iron_weapons & iron_armor & shield
    hard_raid = hard & iron_weapons & (iron_armor | shield)
    beat_raid = village & outpost & (easy_raid | normal_raid | hard_raid)

    basic_wither_kill = diamond_weapons & diamond_armor & potions & can_enchant
    easy_wither = easy & basic_wither_kill & bow
    normal_wither = normal & basic_wither_kill
    hard_wither = hard & (basic_wither_kill | nether | the_end)
    kill_wither = loot_fortress & (easy_wither | normal_wither | hard_wither)

    beacon = kill_wither & diamond_tools & resource_blocks

    respawn_dragon = the_end & nether & furnace
    easy_dragon = easy & diamond_weapons & diamond_armor & bow & potions & can_enchant
    normal_dragon = normal & iron_weapons & iron_armor & bow
    hard_dragon = hard & ((iron_weapons & iron_armor) | (stone_weapons & bed))
    kill_dragon = respawn_dragon & (easy_dragon | normal_dragon | hard_dragon)

    no_compasses = OptionFilter(StructureCompasses, False)

    # entrances

    overworld_compass_1 = Has(f"Structure Compass ({overworld_structure_1.connected_region.name})")
    overworld_compass_2 = Has(f"Structure Compass ({overworld_structure_2.connected_region.name})")
    nether_compass_1 = Has(f"Structure Compass ({nether_structure_1.connected_region.name})")
    nether_compass_2 = Has(f"Structure Compass ({nether_structure_2.connected_region.name})")
    the_end_compass = Has(f"Structure Compass ({the_end_structure.connected_region.name})")
    ocean_compass = Has(f"Structure Compass ({ocean.connected_region.name})")
    dark_forest_compass = Has(f"Structure Compass ({dark_forest.connected_region.name})")
    deep_dark_compass = Has(f"Structure Compass ({deep_dark.connected_region.name})")
    ruins_compass = Has(f"Structure Compass ({ruins.connected_region.name})")
    underground_compass = Has(f"Structure Compass ({underground.connected_region.name})")

    # self.set_rule(new_world, True_)
    self.set_rule(nether_portal, flint_and_steel & (diamond_tools | bucket))
    self.set_rule(end_portal, stronghold & Has("3 Ender Pearls", count=4))
    self.set_rule(overworld_structure_1, can_adventure & (no_compasses | overworld_compass_1))
    self.set_rule(overworld_structure_2, can_adventure & (no_compasses | overworld_compass_2))
    self.set_rule(nether_structure_1, can_adventure & (no_compasses | nether_compass_1))
    self.set_rule(nether_structure_2, can_adventure & (no_compasses | nether_compass_2))
    self.set_rule(the_end_structure, can_adventure & (no_compasses | the_end_compass))
    self.set_rule(ocean, can_adventure & (no_compasses | ocean_compass))
    self.set_rule(dark_forest, can_adventure & (no_compasses | dark_forest_compass))
    self.set_rule(deep_dark, can_adventure & iron_tools & (no_compasses | deep_dark_compass))
    self.set_rule(ruins, can_adventure & (no_compasses | ruins_compass))
    self.set_rule(underground, can_adventure & stone_tools & (no_compasses | underground_compass))

    # events

    defeat_ender_dragon = self.get_location("Ender Dragon")
    defeat_wither = self.get_location("Wither")
    obtain_blaze_rods = self.get_location("Blaze Rods")

    # locations

    who_is_cutting_onions = self.get_location("Who is Cutting Onions?")
    oh_shiny = self.get_location("Oh Shiny")
    suit_up = self.get_location("Suit Up")
    very_very_frightening = self.get_location("Very Very Frightening")
    hot_stuff = self.get_location("Hot Stuff")
    free_the_end = self.get_location("Free the End")
    a_furious_cocktail = self.get_location("A Furious Cocktail")
    # best_friends_forever = self.get_location("Best Friends Forever")
    bring_home_the_beacon = self.get_location("Bring Home the Beacon")
    not_today_thank_you = self.get_location("Not Today, Thank You")
    isnt_it_iron_pick = self.get_location("Isn't It Iron Pick")
    local_brewery = self.get_location("Local Brewery")
    the_next_generation = self.get_location("The Next Generation")
    fishy_business = self.get_location("Fishy Business")
    # hot_tourist_destinations = self.get_location("Hot Tourist Destinations")
    this_boat_has_legs = self.get_location("This Boat Has Legs")
    sniper_duel = self.get_location("Sniper Duel")
    # enter_the_nether = self.get_location("Nether")
    great_view_from_up_here = self.get_location("Great View From Up Here")
    how_did_we_get_here = self.get_location("How Did We Get Here?")
    bullseye = self.get_location("Bullseye")
    spooky_scary_skeleton = self.get_location("Spooky Scary Skeleton")
    two_by_two = self.get_location("Two by Two")
    # stone_age = self.get_location("Stone Age")
    two_birds_one_arrow = self.get_location("Two Birds, One Arrow")
    # we_need_to_go_deeper = self.get_location("We Need to Go Deeper")
    whos_the_pillager_now = self.get_location("Who's the Pillager Now?")
    getting_an_upgrade = self.get_location("Getting an Upgrade")
    tactical_fishing = self.get_location("Tactical Fishing")
    zombie_doctor = self.get_location("Zombie Doctor")
    # the_city_at_the_end_of_the_game = self.get_location("The City at the End of the Game")
    ice_bucket_challenge = self.get_location("Ice Bucket Challenge")
    # remote_getaway = self.get_location("Remote Getaway")
    into_fire = self.get_location("Into Fire")
    war_pigs = self.get_location("War Pigs")
    take_aim = self.get_location("Take Aim")
    total_beelocation = self.get_location("Total Beelocation")
    arbalistic = self.get_location("Arbalistic")
    the_end_again = self.get_location("The End... Again...")
    acquire_hardware = self.get_location("Acquire Hardware")
    not_quite_nine_lives = self.get_location("Not Quite \"Nine\" Lives")
    cover_me_with_diamonds = self.get_location("Cover Me with Diamonds")
    skys_the_limit = self.get_location("Sky's the Limit")
    hired_help = self.get_location("Hired Help")
    # return_to_sender = self.get_location("Return to Sender")
    sweet_dreams = self.get_location("Sweet Dreams")
    you_need_a_mint = self.get_location("You Need a Mint")
    # adventure = self.get_location("Adventure")
    monsters_hunted = self.get_location("Monsters Hunted")
    enchanter = self.get_location("Enchanter")
    voluntary_exile = self.get_location("Voluntary Exile")
    eye_spy = self.get_location("Eye Spy")
    # enter_the_end = self.get_location("The End")
    serious_dedication = self.get_location("Serious Dedication")
    postmortal = self.get_location("Postmortal")
    # monster_hunter = self.get_location("Monster Hunter")
    adventuring_time = self.get_location("Adventuring Time")
    # a_seedy_place = self.get_location("A Seedy Place")
    # those_were_the_days = self.get_location("Those Were the Days")
    hero_of_the_village = self.get_location("Hero of the Village")
    hidden_in_the_depths = self.get_location("Hidden in the Depths")
    beaconator = self.get_location("Beaconator")
    withering_heights = self.get_location("Withering Heights")
    a_balanced_diet = self.get_location("A Balanced Diet")
    subspace_bubble = self.get_location("Subspace Bubble")
    # husbandry = self.get_location("Husbandry")
    country_lode_take_me_home = self.get_location("Country Lode, Take Me Home")
    bee_our_guest = self.get_location("Bee Our Guest")
    what_a_deal = self.get_location("What a Deal!")
    uneasy_alliance = self.get_location("Uneasy Alliance")
    diamonds = self.get_location("Diamonds!")
    # a_terrible_fortress = self.get_location("A Terrible Fortress")
    a_throwaway_joke = self.get_location("A Throwaway Joke")
    # minecraft = self.get_location("Minecraft")
    sticky_situation = self.get_location("Sticky Situation")
    ol_betsy = self.get_location("Ol' Betsy")
    cover_me_in_debris = self.get_location("Cover Me in Debris")
    # is_this_the_end = self.get_location("The End?")
    # the_parrots_and_the_bats = self.get_location("The Parrots and the Bats")
    # a_complete_catalogue = self.get_location("A Complete Catalogue")
    # getting_wood = self.get_location("Getting Wood")
    # time_to_mine = self.get_location("Time to Mine!")
    hot_topic = self.get_location("Hot Topic")
    # bake_bread = self.get_location("Bake Bread")
    the_lie = self.get_location("The Lie")
    on_a_rail = self.get_location("On a Rail")
    # time_to_strike = self.get_location("Time to Strike!")
    # cow_tipper = self.get_location("Cow Tipper")
    when_pigs_fly = self.get_location("When Pigs Fly")
    overkill = self.get_location("Overkill")
    librarian = self.get_location("Librarian")
    overpowered = self.get_location("Overpowered")
    wax_on = self.get_location("Wax On")
    wax_off = self.get_location("Wax Off")
    the_cutest_predator = self.get_location("The Cutest Predator")
    the_healing_power_of_friendship = self.get_location("The Healing Power of Friendship")
    is_it_a_bird = self.get_location("Is It a Bird?")
    is_it_a_balloon = self.get_location("Is It a Balloon?")
    is_it_a_plane = self.get_location("Is It a Plane?")
    surge_protector = self.get_location("Surge Protector")
    light_as_a_rabbit = self.get_location("Light as a Rabbit")
    glow_and_behold = self.get_location("Glow and Behold!")
    whatever_floats_your_goat = self.get_location("Whatever Floats Your Goat!")
    caves_and_cliffs = self.get_location("Caves & Cliffs")
    feels_like_home = self.get_location("Feels Like Home")
    sound_of_music = self.get_location("Sound of Music")
    star_trader = self.get_location("Star Trader")
    birthday_song = self.get_location("Birthday Song")
    bukkit_bukkit = self.get_location("Bukkit Bukkit")
    # it_spreads = self.get_location("It Spreads")
    # sneak_100 = self.get_location("Sneak 100")
    when_the_squad_hops_into_town = self.get_location("When the Squad Hops into Town")
    with_our_powers_combined = self.get_location("With Our Powers Combined!")
    youve_got_a_friend_in_me = self.get_location("You've Got a Friend in Me")
    smells_interesting = self.get_location("Smells Interesting")
    little_sniffs = self.get_location("Little Sniffs")
    planting_the_past = self.get_location("Planting the Past")
    crafting_a_new_look = self.get_location("Crafting a New Look")
    smithing_with_style = self.get_location("Smithing with Style")
    respecting_the_remnants = self.get_location("Respecting the Remnants")
    careful_restoration = self.get_location("Careful Restoration")
    the_power_of_books = self.get_location("The Power of Books")
    isnt_it_scute = self.get_location("Isn't It Scute?")
    shear_brilliance = self.get_location("Shear Brilliance")
    good_as_new = self.get_location("Good as New")
    the_whole_pack = self.get_location("The Whole Pack")
    # minecraft_trials_edition = self.get_location("Minecraft: Trial(s) Edition")
    under_lock_and_key = self.get_location("Under Lock and Key")
    blowback = self.get_location("Blowback")
    who_needs_rockets = self.get_location("Who Needs Rockets?")
    crafters_crafting_crafters = self.get_location("Crafters Crafting Crafters")
    lighten_up = self.get_location("Lighten Up")
    over_overkill = self.get_location("Over-Overkill")
    revaulting = self.get_location("Revaulting")
    stay_hydrated = self.get_location("Stay Hydrated!")
    heart_transplanter = self.get_location("Heart Transplanter")

    self.set_rule(defeat_ender_dragon, kill_dragon)
    self.set_rule(defeat_wither, kill_wither)
    self.set_rule(obtain_blaze_rods, loot_fortress)
    self.set_rule(who_is_cutting_onions, piglin_bartering)
    self.set_rule(oh_shiny, piglin_bartering)
    self.set_rule(suit_up, iron_armor)
    self.set_rule(very_very_frightening, channeling & overworld_villagers)
    self.set_rule(hot_stuff, bucket)
    self.set_rule(free_the_end, kill_dragon)
    self.set_rule(a_furious_cocktail, potions & fishing_rod & nether & village & beacon & trial_chambers)
    self.set_rule(bring_home_the_beacon, beacon)
    self.set_rule(not_today_thank_you, shield)
    self.set_rule(isnt_it_iron_pick, iron_tools)
    self.set_rule(local_brewery, potions)
    self.set_rule(the_next_generation, kill_dragon)
    self.set_rule(fishy_business, fishing_rod)
    self.set_rule(this_boat_has_legs, saddle & fishing_rod)
    self.set_rule(sniper_duel, bow)
    self.set_rule(great_view_from_up_here, combat)
    self.set_rule(how_did_we_get_here, potions & end_city & nether & monument & ancient_city & fishing_rod & bow
                  & beacon & beat_raid)
    self.set_rule(bullseye, bow & iron_tools)
    self.set_rule(spooky_scary_skeleton, loot_fortress)
    self.set_rule(two_by_two, brush & monument & bucket & village)
    self.set_rule(two_birds_one_arrow, crossbow & can_enchant)
    self.set_rule(whos_the_pillager_now, crossbow)
    self.set_rule(getting_an_upgrade, stone_tools)
    self.set_rule(tactical_fishing, bucket)
    self.set_rule(zombie_doctor, cure_zombie)
    self.set_rule(ice_bucket_challenge, diamond_tools)
    self.set_rule(into_fire, loot_fortress)
    self.set_rule(war_pigs, combat)
    self.set_rule(take_aim, bow)
    self.set_rule(total_beelocation, silk_touch)
    self.set_rule(arbalistic, crossbow & piercing_iv)
    self.set_rule(the_end_again, kill_dragon)
    self.set_rule(acquire_hardware, iron_ingots)
    self.set_rule(not_quite_nine_lives, piglin_bartering & resource_blocks)
    self.set_rule(cover_me_with_diamonds, diamond_armor)
    self.set_rule(skys_the_limit, combat)
    self.set_rule(hired_help, resource_blocks & iron_ingots)
    self.set_rule(sweet_dreams, bed | village)
    self.set_rule(you_need_a_mint, respawn_dragon & bottles)
    self.set_rule(monsters_hunted, kill_dragon & kill_wither & beat_raid & bastion & end_city & trial_chambers & lead
                  & monument & ((potions & fishing_rod) | (can_enchant & bucket)))
    self.set_rule(enchanter, can_enchant)
    self.set_rule(voluntary_exile, combat)
    self.set_rule(eye_spy, stronghold)
    self.set_rule(serious_dedication, ancient_debris & netherite_scrap & gold_ingots & diamond_tools)
    self.set_rule(postmortal, beat_raid)
    self.set_rule(adventuring_time, can_adventure & monument & mansion & ancient_city & trail_ruins)
    self.set_rule(hero_of_the_village, beat_raid)
    self.set_rule(hidden_in_the_depths, ancient_debris)
    self.set_rule(beaconator, beacon)
    self.set_rule(withering_heights, kill_wither)
    self.set_rule(a_balanced_diet, bottles & campfire & fishing_rod & enchanted_golden_apple & the_end)
    self.set_rule(subspace_bubble, diamond_tools)
    self.set_rule(country_lode_take_me_home, iron_tools)
    self.set_rule(bee_our_guest, campfire & bottles)
    self.set_rule(what_a_deal, village | cure_zombie)
    self.set_rule(uneasy_alliance, diamond_tools & fishing_rod)
    self.set_rule(diamonds, iron_tools)
    self.set_rule(a_throwaway_joke, combat)
    self.set_rule(sticky_situation, campfire & bottles)
    self.set_rule(ol_betsy, crossbow)
    self.set_rule(cover_me_in_debris, diamond_armor & Has("8 Netherite Scrap", count=2) & ancient_debris)
    self.set_rule(hot_topic, furnace)
    self.set_rule(the_lie, bucket)
    self.set_rule(on_a_rail, iron_tools)
    self.set_rule(when_pigs_fly, saddle & fishing_rod & can_adventure)
    self.set_rule(overkill, (potions & (stone_tools | nether)) | mace)
    self.set_rule(librarian, Has("Enchanting"))
    self.set_rule(overpowered, enchanted_golden_apple)
    self.set_rule(wax_on, campfire & copper_ingots)
    self.set_rule(wax_off, trial_chambers | (campfire & copper_ingots))
    self.set_rule(the_cutest_predator, can_adventure & bucket)
    self.set_rule(the_healing_power_of_friendship, can_adventure & bucket)
    self.set_rule(is_it_a_bird, spyglass)
    self.set_rule(is_it_a_balloon, spyglass)
    self.set_rule(is_it_a_plane, spyglass & respawn_dragon)
    self.set_rule(surge_protector, channeling & overworld_villagers)
    self.set_rule(light_as_a_rabbit, can_adventure & bucket)
    self.set_rule(glow_and_behold, can_adventure)
    self.set_rule(whatever_floats_your_goat, can_adventure)
    self.set_rule(caves_and_cliffs, bucket & iron_tools)
    self.set_rule(feels_like_home, bucket & fishing_rod & saddle)
    self.set_rule(sound_of_music, iron_tools & combat)
    self.set_rule(star_trader, overworld_villagers & bucket & (nether | fortress | piglin_bartering))
    self.set_rule(birthday_song, bucket & iron_tools & (outpost | mansion))
    self.set_rule(bukkit_bukkit, bucket & can_adventure)
    self.set_rule(when_the_squad_hops_into_town, can_adventure & lead & bucket)
    self.set_rule(with_our_powers_combined, can_adventure & lead & bucket)
    self.set_rule(youve_got_a_friend_in_me, outpost | (combat & mansion))
    self.set_rule(smells_interesting, brush)
    self.set_rule(little_sniffs, brush)
    self.set_rule(planting_the_past, brush)
    self.set_rule(crafting_a_new_look, iron_ingots
                  & (loot_fortress | ancient_city | (trail_ruins & brush)
                     | (combat & (outpost | bastion | end_city | mansion | (monument & bucket & can_enchant)))))
    self.set_rule(smithing_with_style, iron_ingots & trail_ruins & brush & loot_fortress & bastion & end_city & mansion
                  & ancient_city & monument & ((fishing_rod & potions) | (bucket & can_enchant)))
    self.set_rule(respecting_the_remnants, brush & (monument | trail_ruins))
    self.set_rule(careful_restoration, brush & (monument | trail_ruins))
    self.set_rule(the_power_of_books, iron_tools)
    self.set_rule(isnt_it_scute, can_adventure & brush)
    self.set_rule(shear_brilliance, can_adventure & brush & iron_ingots)
    self.set_rule(good_as_new, can_adventure & brush)
    self.set_rule(the_whole_pack, can_adventure)
    self.set_rule(under_lock_and_key, combat)
    self.set_rule(blowback, combat)
    self.set_rule(who_needs_rockets, combat)
    self.set_rule(crafters_crafting_crafters, iron_tools)
    self.set_rule(lighten_up, trial_chambers | (loot_fortress & iron_tools & resource_blocks))
    self.set_rule(over_overkill, ominous_vaults)
    self.set_rule(revaulting, ominous_vaults)
    self.set_rule(stay_hydrated, nether | piglin_bartering)
    self.set_rule(heart_transplanter, can_adventure & (silk_touch | (combat & resource_blocks)))


def set_special_rules(self: "MinecraftWorld") -> None:
    multiworld = self.multiworld
    player = self.player

    # Set rules surrounding completion
    bosses = self.options.required_bosses
    postgame_advancements = set()
    if bosses.dragon:
        postgame_advancements.update(Constants.exclusion_info["ender_dragon"])
    if bosses.wither:
        postgame_advancements.update(Constants.exclusion_info["wither"])

    def location_count(state: CollectionState) -> int:
        return len([location for location in multiworld.get_locations(player) if
                    location.address is not None and
                    location.can_reach(state)])

    def defeated_bosses(state: CollectionState) -> bool:
        return ((not bosses.dragon or state.has("Ender Dragon", player))
                and (not bosses.wither or state.has("Wither", player)))

    egg_shards = min(self.options.egg_shards_required.value, self.options.egg_shards_available.value)
    completion_requirements = lambda state: (location_count(state) >= self.options.advancement_goal
                                             and state.has("Dragon Egg Shard", player, egg_shards))
    multiworld.completion_condition[player] = lambda state: completion_requirements(state) and defeated_bosses(state)

    # Set exclusions on hard/unreasonable/postgame
    excluded_advancements = set()
    if not self.options.include_hard_advancements:
        excluded_advancements.update(Constants.exclusion_info["hard"])
    if not self.options.include_unreasonable_advancements:
        excluded_advancements.update(Constants.exclusion_info["unreasonable"])
    if not self.options.include_postgame_advancements:
        excluded_advancements.update(postgame_advancements)
    exclusion_rules(multiworld, player, excluded_advancements)
