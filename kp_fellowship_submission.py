import curses
from itertools import permutations
import random
import time
import math
import io

HEART = '♥'
SPADE = '♠'
DIAMOND = '♦'
CLUB = '♣'
SUITES = [HEART, SPADE, DIAMOND, CLUB]
# using spaces so all cards have same size
# if you want it to be easier, shorten the list of ranks
RANKS = ['2 ', '3 ', '4 ', '5 ', '6 ', '7 ', '8 ', '9 ', '10', 'J ', 'Q ', 'K ', 'A ']
CARDS_PER_SUITE = [[this_suite + this_rank for this_rank in RANKS] for this_suite in SUITES]
CARDS = [card for suite in CARDS_PER_SUITE for card in suite]
CARD_SIZE = len(CARDS[0])
RED_PAIR = 1
BLACK_PAIR = 2
SUITE_COLOR_PATTERN = {HEART: RED_PAIR, DIAMOND: RED_PAIR, SPADE: BLACK_PAIR, CLUB: BLACK_PAIR}
BACK_PAIR = 3
CARD_BACK = '*'*CARD_SIZE
ROWS = len(SUITES)
COLUMNS = len(RANKS)
WRONG_MATCH_PAUSE = 1
N_PLAYERS = 3
assert N_PLAYERS >= 1, "need at least one player"

INSTRUCTIONS = """
This is a Python implementation of Memory! Click two cards to flip them when it's your turn, and if they're a match you score a point. The player with the most points at the end wins. Try to remember what cards have been shown before! The person with their player highlighted is supposed to go next.
\n
(press any key to continue)
"""

def main(stdscr):
    # Clear screen
    stdscr.clear()

    # check if the terminal is big enough for the current settings
    max_y, max_x = stdscr.getmaxyx()
    needed_y = ROWS*2 + N_PLAYERS + 2
    assert max_y >= needed_y, "terminal is not tall enough, need at least %d rows"%needed_y
    # get the maximum possible size of a player score message
    # NOTE: this assumes message is of the form "player %d score: %d"
    max_player_score_message = 19 + int(math.log10(len(CARDS) // 2)) + int(math.log10(N_PLAYERS))
    # and compare that to the max size needed for the cards
    # along with the size of the keyboard shortcuts method
    needed_x = max(COLUMNS*(CARD_SIZE + 1), max_player_score_message, 22)
    assert max_x >= COLUMNS*(CARD_SIZE + 1), "terminal is not wide enough, need at least %d columns"%needed_x

    curses.mousemask(curses.BUTTON1_CLICKED)

    # initialize color profiles
    curses.init_pair(RED_PAIR, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(BLACK_PAIR, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(BACK_PAIR, curses.COLOR_YELLOW, curses.COLOR_BLUE)

    # make initial screen
    locations = get_card_locations()
    possible_clicks = set(locations)
    show_backs_of_cards(stdscr, locations)

    # stdscr.refresh()

    # get randomly ordered cards
    # using sample instead of shuffle because shuffle shuffles in-place
    cards = random.sample(CARDS, len(CARDS))
    where_cards = {location: cards[i] for i, location in enumerate(locations)}
    clicked_cards = []
    clicked_locations = []
    flipped_up = set()
    clicked = 0
    flips = 0
    matches_per_player = [0 for i in range(N_PLAYERS)]
    next_player = 0

    if N_PLAYERS == 1:
        update_stats(stdscr, flips, matches_per_player[0])
    else:
        update_stats_multiplayer(stdscr, flips, matches_per_player, next_player)
    display_shortcuts(stdscr)

    stdscr.refresh()

    while True:
        # listen for event
        event = stdscr.getch()
        if event == ord('q'):
            # exit the game
            break

        elif event == ord('i'):
            # display the instructions
            new_win = curses.newwin(max_y, max_x)
            display_instructions(new_win)

            new_win.touchwin()
            new_win.refresh()
            new_win.getch()
            del new_win

            stdscr.touchwin()
            stdscr.refresh()

        elif event == curses.KEY_MOUSE:
            # process a click, and maybe a clicked card
            _, mx, my, _, _ = curses.getmouse()
            click_location = get_location_of_click(my, mx)
            if click_location not in possible_clicks:
                # clicked something we shouldn't be able to click
                continue
            if click_location in clicked_locations:
                # clicked the same card
                continue
            if click_location in flipped_up:
                # clicked a card already flipped up
                continue

            # get which card was clicked and flip it
            clicked_card = where_cards[click_location]
            color_pair = SUITE_COLOR_PATTERN[clicked_card[0]]
            stdscr.addstr(click_location[0], click_location[1], clicked_card, curses.color_pair(color_pair))

            clicked_cards.append(clicked_card)
            clicked_locations.append(click_location)
            clicked += 1

            stdscr.refresh()

        if clicked == 2:
            # we've clicked on two cards, check if they're a match
            card1, card2 = clicked_cards
            color_match = SUITE_COLOR_PATTERN[card1[0]] == SUITE_COLOR_PATTERN[card2[0]]
            rank_match = card1[1:] == card2[1:]
            if not color_match or not rank_match:
                # pause so they can read the card
                time.sleep(WRONG_MATCH_PAUSE)
                # flip those cards back over
                for location in clicked_locations:
                    stdscr.addstr(location[0], location[1], CARD_BACK, curses.color_pair(BACK_PAIR))
            else:
                flipped_up.update(clicked_locations)
                matches_per_player[next_player] += 1

            clicked_cards = []
            clicked_locations = []
            clicked = 0
            flips += 1
            next_player = (next_player + 1)%N_PLAYERS

            if N_PLAYERS == 1:
                update_stats(stdscr, flips, matches_per_player[0])
            else:
                update_stats_multiplayer(stdscr, flips, matches_per_player, next_player)

            stdscr.refresh()

        if len(flipped_up) == len(cards):
            flip_cards_back_and_forth(stdscr, locations, cards)

def flip_cards_back_and_forth(stdscr, locations, cards, n_flips = 3, rows = ROWS, columns = COLUMNS):
    # animation for the end of the game
    for i in range(n_flips):
        show_backs_of_cards(stdscr, locations, rows = rows, columns = columns)
        stdscr.refresh()
        time.sleep(.5)
        show_all_cards(stdscr, locations, cards = cards, rows = rows, columns = columns)
        stdscr.refresh()
        time.sleep(.5)

def get_card_locations(rows = ROWS, columns = COLUMNS):
    # initialize the locations of the cards
    locations = []
    for row in range(rows):
        for column in range(columns):
            locations.append((row*2, column*(CARD_SIZE + 1)))

    return locations

def update_stats(stdscr, flips, matches, row = ROWS*2, column = 0):
    # we can update both at once because curses won't bother
    # rerendering matches unless there's a change
    flips_message = "flips so far: %d"%flips
    stdscr.addstr(row, column, flips_message)
    matches_message = "matches: %d"%matches
    stdscr.addstr(row+1, column, matches_message)

def update_stats_multiplayer(stdscr, flips, matches_per_player, next_turn, row = None, column = 0):
    if row is None:
        row = ROWS*2
    # display score per player
    # and highlight the player whose turn it is next
    flips_message = "flips so far: %d"%flips
    stdscr.addstr(row, column, flips_message)

    for i, matches in enumerate(matches_per_player):
        # define and display these individually
        # so that we can highlight the player's index
        # but not their score
        player_message = "player %d"%i
        if i == next_turn:
            stdscr.addstr(row + i + 1, column, player_message, curses.color_pair(BACK_PAIR))
        else:
            stdscr.addstr(row + i + 1, column, player_message)

        matches_message = " matches: %d"%matches
        stdscr.addstr(row + i + 1, column+len(player_message), matches_message)

def display_shortcuts(stdscr, row = None, column = 0):
    # display the keyboard shortcuts
    if row is None:
        row = ROWS*2 + N_PLAYERS + 2
    stdscr.addstr(row, column, "(q)uit, (i)nstructions")

def display_instructions(stdscr, row = 0, column = 0):
    # display the instructions
    # this is to be run in a seperate window
    stdscr.addstr(row, column, INSTRUCTIONS)


def get_location_of_click(x, y):
    # need to round coordinates down to nearest card location
    loc_x = x - (x%2)
    loc_y = y - (y%(CARD_SIZE + 1))

    return loc_x, loc_y

def show_all_cards(stdscr, locations, rows = ROWS, columns = COLUMNS, cards = CARDS):
    # show all of the cards face-forward
    for i, location in enumerate(locations):
        card = CARDS[i]
        color_pair = SUITE_COLOR_PATTERN[card[0]]
        stdscr.addstr(location[0], location[1], card, curses.color_pair(color_pair))

def show_backs_of_cards(stdscr, locations, rows = ROWS, columns = COLUMNS):
    # show just the backs of the cards
    for location in locations:
        stdscr.addstr(location[0], location[1], CARD_BACK, curses.color_pair(BACK_PAIR))

if __name__ == "__main__":
    curses.wrapper(main)