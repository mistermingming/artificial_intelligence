#!/usr/bin/python
import copy
import pygame
import random
import argparse
import time

from WarNode import *

SQUARE_SIZE = 60
GRID_SIZE = 6

RGB_WHITE = (255, 255, 255)
RGB_BLACK = (0, 0, 0)
RGB_GRAY = (125, 125, 125)
RGB_RED = (255, 0, 0)
RGB_BLUE = (0, 0, 255)
RGB_GREEN = (0, 255, 0)

GAME = "battle"
# GAME = "battle"
# GAME = "attrition"
# GAME = "duel"
# GAME="flipcoin"
ATTRITION_RATE = 0.7

BLUE_AI = -1
GREEN_AI = -1

DEPTH = 3

# Initialize game to initialize FONT(s) for below functions.
pygame.font.init()
FONT = pygame.font.Font(None,50)
SMALL_FONT= pygame.font.Font(None,30)

def iround(integer):
    """iround(number) -> integer
    Round a number to the nearest integer."""
    return int(round(integer) - .5) + (integer > 0)


def on_board(coord):
    if coord[0] in range(0, GRID_SIZE) and coord[1] in range(0, GRID_SIZE):
            return True
    else:
        return False

def update_resources(board_ra_temp):
    blue_resources = 0
    green_resources = 0
    for x in range(0, GRID_SIZE):
        for y in range(0, GRID_SIZE):
            if board_ra_temp[x][y].player != None:
                board_ra_temp[x][y].resources = board_ra_temp[x][y].resources * ATTRITION_RATE
                blue_resources += board_ra_temp[x][y].resources*(board_ra_temp[x][y].player +1)/2
                green_resources -= board_ra_temp[x][y].resources*(board_ra_temp[x][y].player-1)/2
    return blue_resources, green_resources


def apply_blitz_rule(board_ra_temp, click_coord, player):
    board_ra_temp[click_coord[0]][click_coord[1]].player = player
    directions = [(0,1), (1,0), (0,-1), (-1,0)]
    blitz = False
    captures = []
    for d in directions:
        x = click_coord[0] + d[0]
        y = click_coord[1] + d[1]
        if on_board((x,y)): 
            temp = board_ra_temp[x][y].player
            if temp == player:
                blitz = True
            elif temp == - player:
                captures.append((x,y))
    if blitz:
        for c in captures:
            board_ra_temp[c[0]][c[1]].player = player
    return captures

def apply_flipcoin_blitz(board_ra_temp, click_coord, player):
    prob = random.random()
    if prob > 0.5:
        apply_blitz_rule(board_ra_temp, click_coord, player)
    board_ra_temp[click_coord[0]][click_coord[1]].player = player

def apply_battle_rule(board_ra_temp, click_coord, player, blue_score, green_score, blue_count, green_count):
    if ATTRITION_RATE == 1:
        blue_resources = blue_score
        green_resources = green_score
    else:
        blue_resources, green_resources = update_resources(board_ra_temp)
    blue_resources += board_ra_temp[click_coord[0]][click_coord[1]].score*(player + 1)/2  #if player = blue, +=score, else +=0, add accumulate attrition
    green_resources -= board_ra_temp[click_coord[0]][click_coord[1]].score*(player -1)/2  #if player = green, +=score, else +=0, add accumulate attrition
    board_ra_temp[click_coord[0]][click_coord[1]].player = player
    blue_count += (player + 1)/2 #if player = blue, +=1, else +=0
    green_count -= (player -1)/2 #if player = green, +=1, else +=0
    if blue_count == 0:
        blue_force = 0.00
    else:
        blue_force = 1.0*blue_resources/blue_count
    if green_count == 0:
        green_force = 0.00
    else:
        green_force = 1.0*green_resources/green_count
    # print accum_attrition
    # print blue_force, green_force

    directions = [(0,1), (1,0), (0,-1), (-1,0)]
    battle = False
    captures = []
    allies = 1
    for d in directions:
        x = click_coord[0] + d[0]
        y = click_coord[1] + d[1]
        if on_board((x,y)): 
            temp = board_ra_temp[x][y].player
            if temp == player:
                battle = True
                allies += 1
            elif temp == - player:
                captures.append((x,y))

    if battle:
        for c in captures:
            enemies = 1
            for d in directions:
                x = c[0] + d[0]
                y = c[1] + d[1]
                if on_board((x,y)):
                    temp = board_ra_temp[x][y].player
                    if temp == -player:
                        enemies += 1
            # print allies, enemies, (blue_force*(player + 1)/2 - green_force*(player -1)/2)*allies, (blue_force*(-player + 1)/2 + green_force*(player +1)/2)*enemies
            if (blue_force*(player + 1)/2 - green_force*(player -1)/2)*allies - (blue_force*(-player + 1)/2 + green_force*(player +1)/2)*enemies >0:
                # if allies is stronger than enemies at the battle
                board_ra_temp[c[0]][c[1]].player = player
                blue_count +=player # if player = blue, +=1, else -=1
                green_count -=player #if player = green, +=1, else -=1

    return blue_count, green_count


def apply_duel_rule(board_ra_temp, click_coord, player, blue_score, green_score, blue_count, green_count):
    if ATTRITION_RATE == 1:
        blue_resources = blue_score
        green_resources = green_score
    else:
        blue_resources, green_resources = update_resources(board_ra_temp)
    blue_resources += board_ra_temp[click_coord[0]][click_coord[1]].score*(player + 1)/2 #if player = blue, +=score, else +=0, add accumulate attrition
    green_resources -= board_ra_temp[click_coord[0]][click_coord[1]].score*(player -1)/2 #if player = green, +=score, else +=0, add accumulate attrition
    board_ra_temp[click_coord[0]][click_coord[1]].player = player
    blue_count += (player + 1)/2 #if player = blue, +=1, else +=0
    green_count -= (player -1)/2 #if player = green, +=1, else +=0
    if blue_count == 0:
        blue_force = 0.0
    else:
        blue_force = 1.0*blue_resources/blue_count
    if green_count == 0:
        green_force = 0.0
    else:
        green_force = 1.0*green_resources/green_count
    #print blue_force, green_force

    directions = [(0,1), (1,0), (0,-1), (-1,0)]
    duel = False
    captures = []
    for d in directions:
        x = click_coord[0] + d[0]
        y = click_coord[1] + d[1]
        if on_board((x,y)): 
            temp = board_ra_temp[x][y].player
            if temp == player:
                duel = True
            elif temp == - player:
                captures.append((x,y))

    if duel and player*(blue_force - green_force) > 0:
        for c in captures:
            board_ra_temp[c[0]][c[1]].player = player
            blue_count +=player # if player = blue, +=1, else -=1
            green_count -=player #if player = green, +=1, else -=1

    return blue_count, green_count


def expand_node(parent, click_coord, node_count):
    blue_score = 0
    green_score = 0
    board_ra_temp = copy.deepcopy(parent[0])
    #Keep track of the new spots taken by splitz
    blitz_captured = []
    if GAME == "battle":
        blue_count, green_count = apply_battle_rule(board_ra_temp, click_coord, parent[1], parent[2], parent[3], parent[4], parent[5])
    elif GAME == "duel":
        blue_count, green_count = apply_duel_rule(board_ra_temp, click_coord, parent[1], parent[2], parent[3], parent[4], parent[5])
    else:
        blitz_captured = apply_blitz_rule(board_ra_temp, click_coord, parent[1])
        blue_count = None
        green_count = None
    for x in range(0, GRID_SIZE):
        for y in range(0, GRID_SIZE):
            temp = board_ra_temp[x][y].player
            if (x, y) in blitz_captured and GAME == "flipcoin":
                if temp == 1:
                    blue_score += 0.5 * board_ra_temp[x][y].score*board_ra_temp[x][y].player
                elif temp == -1:
                    green_score -= 0.5 * board_ra_temp[x][y].score*board_ra_temp[x][y].player
            if temp==1:
                blue_score += board_ra_temp[x][y].score*board_ra_temp[x][y].player
            elif temp==-1:
                green_score -= board_ra_temp[x][y].score*board_ra_temp[x][y].player
    return (board_ra_temp, -parent[1], blue_score, green_score, blue_count, green_count), node_count+1


def monte_carlo(parent, empty_spaces):
    if len(empty_spaces) == 0:
        return parent
    else:
        click_coord = random.choice(empty_spaces)
        child_empty_spaces = copy.copy(empty_spaces)
        child_empty_spaces.remove(click_coord)
        child, node_count_temp = expand_node(parent, click_coord, 0)
        candidate = monte_carlo(child, child_empty_spaces)
        return candidate


def monte_carlo_simulation(parent, empty_spaces, number):
    blue_score_sum = 0
    green_score_sum = 0
    for n in range(0, number):
        model = monte_carlo(parent, empty_spaces)
        blue_score_sum += model[2]
        green_score_sum += model[3]
    return iround(blue_score_sum/number), iround(green_score_sum/number)


def minimax(parent, empty_spaces, depth, node_count):
    player = parent[1]
    if depth == 0 or len(empty_spaces) == 0:
        # Monte_Carlo
        # blue_score_evaluation, green_score_evaluation = monte_carlo_simulation(parent, empty_spaces, 3)
        # leaf = (parent[0], parent[1], blue_score_evaluation, green_score_evaluation, parent[4], parent[5])
        # return leaf, None, node_count # evaluation function here
        return parent, None, node_count
    if player == 1:
        best_candidate = (None, player, -1000000, 0, 0, 0, 0)
        best_click_coord = None
        for click_coord in empty_spaces:
            child_empty_spaces = copy.copy(empty_spaces)
            child_empty_spaces.remove(click_coord)
            child, node_count = expand_node(parent, click_coord, node_count)
            candidate, next_best_coord, node_count = minimax(child, child_empty_spaces, depth - 1, node_count)
            if candidate[2] - candidate[3] > best_candidate[2] - best_candidate[3]:
                best_candidate = candidate
                best_click_coord = click_coord
                #print best_click_coord
        return best_candidate, best_click_coord, node_count
    elif player == -1:
        best_candidate = (None, player, 1000000, 0, 0, 0, 0)
        best_click_coord = None
        for click_coord in empty_spaces:
            child_empty_spaces = copy.copy(empty_spaces)
            child_empty_spaces.remove(click_coord)
            child, node_count = expand_node(parent, click_coord, node_count)
            candidate, next_best_coord, node_count = minimax(child, child_empty_spaces, depth - 1, node_count)
            if candidate[2] - candidate[3] < best_candidate[2] - best_candidate[3]:
                best_candidate = candidate
                best_click_coord = click_coord
        return best_candidate, best_click_coord, node_count


def alphabeta(parent, empty_spaces, alpha, beta, depth, node_count):
    player = parent[1]
    if depth == 0 or len(empty_spaces) == 0:
        # Monte_Carlo
        #blue_score_evaluation, green_score_evaluation = monte_carlo_simulation(parent, empty_spaces, 10)
        #leaf = (parent[0], parent[1], blue_score_evaluation, green_score_evaluation, parent[4], parent[5])
        #return leaf, None, node_count # evaluation function here
        return parent, None, node_count
        
    if player == 1:
        best_candidate = (None, player, -1000000, 0, 0, 0, 0)
        best_click_coord = None
        for click_coord in empty_spaces:
            child_empty_spaces = copy.copy(empty_spaces)
            child_empty_spaces.remove(click_coord)
            child, node_count = expand_node(parent, click_coord, node_count)
            candidate, next_best_coord, node_count = alphabeta(child, child_empty_spaces, alpha, beta, depth - 1, node_count)
            if candidate[2] - candidate[3] > best_candidate[2] - best_candidate[3]:
                best_candidate = candidate
                best_click_coord = click_coord
            if best_candidate[2] - best_candidate[3] > alpha:
                alpha = best_candidate[2] - best_candidate[3]
            if alpha >= beta:
                break
                #print best_click_coord
        return best_candidate, best_click_coord, node_count

    elif player == -1:
        best_candidate = (None, player, 1000000, 0, 0, 0, 0)
        best_click_coord = None
        for click_coord in empty_spaces:
            child_empty_spaces = copy.copy(empty_spaces)
            child_empty_spaces.remove(click_coord)
            child, node_count = expand_node(parent, click_coord, node_count)
            candidate, next_best_coord, node_count = alphabeta(child, child_empty_spaces, alpha, beta, depth - 1, node_count)
            if candidate[2] - candidate[3] < best_candidate[2] - best_candidate[3]:
                best_candidate = candidate
                best_click_coord = click_coord
            if best_candidate[2] - best_candidate[3] < beta:
                beta = best_candidate[2] - best_candidate[3]
            if alpha >= beta:
                break
        return best_candidate, best_click_coord, node_count


def do_ai(board_ra, player, blue_score, green_score, blue_count, green_count, depth, ai_mode): ######working
    empty_spaces = []
    for x in range(0, GRID_SIZE):
        for y in range(0, GRID_SIZE):
            if board_ra[x][y].player == None:
                empty_spaces.append((x,y))
    #print len(empty_spaces)
    parent = (copy.deepcopy(board_ra), player, blue_score, green_score, blue_count, green_count)
    node_count = 0
    if ai_mode == 1:
        best_candidate, best_click_coord, node_count = minimax(parent, empty_spaces, depth, node_count)
        #print(best_click_coord)
    else:
        alpha = -1000000
        beta = 1000000
        best_candidate, best_click_coord, node_count = alphabeta(parent, empty_spaces, alpha, beta, depth, node_count)
        #print(best_click_coord)
    #board_ra[best_click_coord[0]][best_click_coord[1]].player = player

    return best_click_coord, node_count


def draw_board(screen, board_ra): # draw the board.
    for x in range(0, GRID_SIZE):
        for y in range(0, GRID_SIZE):
            letter_pos = ((SQUARE_SIZE+1)*x + SQUARE_SIZE/4, (SQUARE_SIZE+1)*y + SQUARE_SIZE/4)
            square = ((SQUARE_SIZE+1)*x, (SQUARE_SIZE+1)*y, SQUARE_SIZE, SQUARE_SIZE)
            pygame.draw.rect(screen, RGB_WHITE, square)
            text = FONT.render(str(board_ra[x][y].score), True, RGB_BLACK)
            screen.blit(text, letter_pos)


def draw_cicle(screen, coord, player): # draw circle on the given coodrination. 
    if player == 1:
        color = RGB_BLUE
    elif player == -1:
        color = RGB_GREEN
    square = ((SQUARE_SIZE+1)*coord[0], (SQUARE_SIZE+1)*coord[1], SQUARE_SIZE, SQUARE_SIZE)
    pygame.draw.ellipse(screen, color, square, 10)


def write_status(screen, blue_score, green_score): # draw the board.
    rectangle = ((SQUARE_SIZE+1)*0, (SQUARE_SIZE+1)*GRID_SIZE, (SQUARE_SIZE+1) * GRID_SIZE -1, SQUARE_SIZE)
    pygame.draw.rect(screen, RGB_BLACK, rectangle)
    sentence_pos_1 = ((SQUARE_SIZE+1)*0 + SQUARE_SIZE/4, (SQUARE_SIZE+1)*GRID_SIZE + 3*SQUARE_SIZE/5)
    sentence_pos_2 = ((SQUARE_SIZE+1)*0 + SQUARE_SIZE/4, (SQUARE_SIZE+1)*GRID_SIZE + SQUARE_SIZE/5)    
    sentence_1 = "Blue: " + str(blue_score)
    sentence_2 = "Green: " + str(green_score)
    text_1 = SMALL_FONT.render(sentence_1, True, RGB_WHITE)
    text_2 = SMALL_FONT.render(sentence_2, True, RGB_WHITE)
    screen.blit(text_1, sentence_pos_1)
    screen.blit(text_2, sentence_pos_2)


def click(screen, board_ra, player):
    while True:
        e = pygame.event.wait()
        if e.type == pygame.QUIT:
            return False, (-GRID_SIZE, -GRID_SIZE)
        elif e.type == pygame.MOUSEBUTTONDOWN:
            x = int(e.pos[0]/(SQUARE_SIZE+1))
            y = int(e.pos[1]/(SQUARE_SIZE+1))
            if on_board((x,y)) and board_ra[x][y].player == None:
                #board_ra[x][y].player = player
                return True, (x, y)


def end_turn(screen, board_ra):
    blue_score = 0
    green_score = 0
    for x in range(0, GRID_SIZE):
        for y in range(0, GRID_SIZE):
            temp = board_ra[x][y].player
            if temp==1:
                blue_score += board_ra[x][y].score*board_ra[x][y].player
                draw_cicle(screen, (x,y), temp)
            elif temp==-1:
                green_score -= board_ra[x][y].score*board_ra[x][y].player
                draw_cicle(screen, (x,y), temp)
    pygame.display.flip()
    return blue_score, green_score


def game():
    board_file = parse_cl_args()
    board_ra = read_board(board_file)

    click_coord = (-GRID_SIZE, -GRID_SIZE)
    player = 1 # who will play the game first
    turn = 0
    blue_score = 0
    green_score = 0
    blue_count = 0
    green_count = 0
    game_running = True
    game_continue = False
    accum_attrition = 0

    blue_node_count_sum = 0
    green_node_count_sum = 0
    blue_move_time_sum = 0
    green_move_time_sum = 0

    screen = pygame.display.set_mode(((SQUARE_SIZE+1) * GRID_SIZE -1, (SQUARE_SIZE+1)* GRID_SIZE -1 + SQUARE_SIZE))
    pygame.display.set_caption("MP2 2 "+ GAME)
    draw_board(screen, board_ra)
    write_status(screen, blue_score, green_score)
    pygame.display.flip()

    while game_running:
        if player==1: # blue's turn
            blue_time_start = time.time()
            if BLUE_AI != False:
                click_coord, node_count = do_ai(board_ra, player, blue_score, green_score, blue_count, green_count, DEPTH, BLUE_AI)
                print ("Blue's node: " + str(node_count))
                blue_node_count_sum += node_count
            else:
                game_running, click_coord = click(screen, board_ra, player)
            #print click_coord
            blue_time_end = time.time()
            blue_move_time_sum += (blue_time_end - blue_time_start)
        else: # green's turn
            green_time_start = time.time()
            if GREEN_AI != False:
                click_coord, node_count = do_ai(board_ra, player, blue_score, green_score, blue_count, green_count, DEPTH, GREEN_AI)
                print ("Green's node: " + str(node_count))
                green_node_count_sum += node_count
            else:
                game_running, click_coord = click(screen, board_ra, player)
            green_time_end = time.time()
            green_move_time_sum += (green_time_end - green_time_start)

        if GAME == "battle":
            blue_count, green_count = apply_battle_rule(board_ra, click_coord, player, blue_score, green_score, blue_count, green_count)
        elif GAME == "duel":
            blue_count, green_count = apply_duel_rule(board_ra, click_coord, player, blue_score, green_score, blue_count, green_count)
        elif GAME == "flipcoin":
            apply_flipcoin_blitz(board_ra, click_coord, player)
        else:
            apply_blitz_rule(board_ra, click_coord, player)
        player = -player
        turn += 1
        draw_board(screen, board_ra)
        blue_score, green_score = end_turn(screen, board_ra)
        write_status(screen, blue_score, green_score)
        pygame.display.flip()

        #for x in range(0, GRID_SIZE):
        #    for y in range(0, GRID_SIZE):
        #        print str(board_ra[x][y].resources)

        if turn == GRID_SIZE*GRID_SIZE :
            print "game over"
            print ("Avergae of blue's node: " + str(1.0*blue_node_count_sum/18))
            print ("Avergae of gree's node: " + str(1.0*green_node_count_sum/18))
            print ("Expanded blue's node: " + str(1.0*blue_node_count_sum))
            print ("Expanded green's node: " + str(1.0*green_node_count_sum))
            print("green move time: " + str(green_move_time_sum / 18))
            print("blue move time: " + str(blue_move_time_sum / 18))

            game_running = False
            game_continue = True
            write_status(screen, blue_score, green_score)
            if blue_score > green_score:
                game_over_text = FONT.render("Blue WIN",1, RGB_WHITE, RGB_BLACK)
            elif blue_score < green_score:
                game_over_text = FONT.render("Green WIN",1, RGB_WHITE,RGB_BLACK)
            else:
                game_over_text = FONT.render("DRAW",1,RGB_BLACK,RGB_GRAY)
            screen.blit(game_over_text, ((SQUARE_SIZE+1) * GRID_SIZE -1 -3* SQUARE_SIZE, (SQUARE_SIZE+1)*GRID_SIZE + SQUARE_SIZE/3))
            pygame.display.flip()

    return game_continue


def main():
    game_continue = game()
    while game_continue:
        e = pygame.event.wait()
        if e.type == pygame.QUIT: break
        elif e.type == pygame.MOUSEBUTTONDOWN: game()

if __name__ == '__main__':
    main()
