#!/usr/bin/python3

import argparse
import heapq
import os
import sys
from collections import deque
import pygame

SQUARE_SIZE = 20
PATH_RADIUS = 4


CWD = os.path.dirname(os.path.abspath(__file__))
arg_parser = argparse.ArgumentParser()

arg_parser.add_argument('maze_file',
                        help = 'file containing ASCII maze',
                        nargs = '?')
arg_parser.add_argument('alg',
                        help = 'search algorithm to use',
                        nargs = '?')
arg_parser.add_argument('move_cost',
                        help = 'forward movement cost',
                        nargs = '?',
                        default = 1)
arg_parser.add_argument('turn_cost',
                        help = 'turn cost',
                        nargs = '?',
                        default = 0)

def parse_cl_args():
    """Parse and return command-line arguments.

    Returns:
        maze_file: The name of the input maze file.
        alg: The search algorithm to use.
    """
    cl_args = arg_parser.parse_args()
    maze_file = CWD + '/' + os.path.relpath(cl_args.maze_file, CWD)
    alg = cl_args.alg
    move_cost = int(cl_args.move_cost)
    turn_cost = int(cl_args.turn_cost)
    return maze_file, alg, move_cost, turn_cost

def read_file(fil):
    """Reads a file and returns a list of the lines in it.

    Args:
        fil: The name of the file to read.

    Returns:
        lines: The list of lines from the file.

    """
    lines = []
    with open(fil) as f:
        lines = f.readlines()
    return lines

def populate_array_from_lines(maze_rows, maze_ra, isDot):
    """Populates an array given string rows of equal length.

    Assumes that each string row in the list of rows contains the same
    number of characters. One character is assigned to each location
    in the array. The given array is assumed to have the correct row
    and column lengths.

    Args:
        maze_rows: The list of lines representing the rows of the
            maze.
        maze_ra: The array to write the characters of the maze to.
        isDot: if the goal of this maze is to eat up dots instead of finding exit
    Returns:
        maze_ra: The populated array.
        start: The (r,c) coordinates of 'P', the start point.
        end: The (r,c) coordinates of '.', the end point.
        dots: a non-empty array if the goal is to eat dots, else an empty array
    """
    r_idx = c_idx = 0
    start = end = ()
    ghost_start = []
    dots = []
    walls = []
    for row in maze_rows:
        row = row.strip()
        for c in row:
            if c == '%':
                walls.append((r_idx, c_idx))
            elif c == 'P':
                start = (r_idx, c_idx)
            elif c == '.':
                dots.append((r_idx, c_idx))
            elif c == 'G':
                ghost_start.append((r_idx, c_idx))
            maze_ra[r_idx][c_idx] = c
            c_idx += 1
        # Reset all the way to the left, move down one row.
        c_idx = 0
        r_idx += 1
    return maze_ra, start, dots, ghost_start, walls 

def create_maze_array(maze_rows, isDot):
    """Creates an array to contain the characters in a maze.

    Characters in the maze are to be referenced by coordinates (r,c),
    where r is the number of rows from the top to go down, and c is
    the number of columns from the left to go right.

    Args:
        maze_rows: The list of lines representing the rows of the
            maze.

    Returns:
        maze_ra: The array populated with the maze characters.
        start: The (r,c) coordinates of 'P', the start point.
        end: The (r,c) coordinates of '.', the end point.
    """
    if maze_rows == []:
        return []
    row_len = len(maze_rows[0].strip()) # i.e. #columns
    col_len = len(maze_rows) # i.e. #rows
    # Let array coordinates be (#rows down, #cols right).
    maze_ra = [['' for r in range(row_len)] for c in range(col_len)]
    maze_ra, start, end, ghost_start, dots = populate_array_from_lines(maze_rows, maze_ra, isDot)
    return maze_ra, start, end, ghost_start, dots

def is_in_bounds(maze_ra, coord):
    """Checks if a coordinate is within the maze.

    Args:
        maze_ra: The array populated with the maze characters.
        coord: The (r,c) tuple coordinate to check.

    Returns:
        is_within: True if the coordinates are within the maze.
    """
    if (coord[0] < 0 or coord[1] < 0):
        return False
    if (coord[0] >= len(maze_ra) or coord[1] >= len(maze_ra[1])):
        return False
    return True

def can_move_to(maze_ra, coord):
    """Checks if coordinate can be moved to, i.e. is not a wall.

    Args:
        maze_ra: The array populated with the maze characters.
        coord: The (r,c) tuple coordinate to check.

    Returns:
        can_move: False if '%'. True if ' ', 'P', or '.'.
    """
    if not is_in_bounds(maze_ra, coord):
        return False
    if maze_ra[coord[0]][coord[1]] == '%':
        return False
    return True

def add_tuples(one, two):
    """Adds two tuples of two integers each.

    Args:
        one: The first tuple, containing two elements.
        two: The second tuple, containing two elements.

    Returns:
        summmed: The tuple where corresponding elements were summed.
    """
    first = one[0] + two[0]
    second = one[1] + two[1]
    summed = (first, second)
    return summed

def ghost_moves(maze_ra, ghost_curr, ghost_direction):
    """Rotates the direction of each ghost corresponding to its path.

    Args:
        ghost_curr: The current position of each ghost
        ghost_direction: The past direction of each ghost.

    Returns:
        ghost_temp: The possible future position of each ghost is returned.
        ghost_direction_temp: The possible direction of each ghost is returned. 
    """
    ghost_direction_temp = ghost_direction
    ghost_temp = ghost_curr
    for d in [(0,-1),(0,1),(-1,0),(1,0)]: #set the order of the searching directions front(default)->right->left->rear->front(the ghost doesn't move)
        ghost_temp = add_tuples(ghost_curr, ghost_direction_temp)
        if maze_ra[ghost_temp[0]][ghost_temp[1]] == 'g' or maze_ra[ghost_temp[0]][ghost_temp[1]] == 'G':
            pass
        else:
            ghost_direction_temp = (d[0]*ghost_direction[0] + d[1]*ghost_direction[1], - d[1]*ghost_direction[0] + d[0]*ghost_direction[1])
            ghost_temp = ghost_curr #in the case the ghost does not move
    #print(ghost_temp)
    return ghost_temp, ghost_direction_temp

def can_escape_from_ghost_to(maze_ra, neighbor, curr, ghost_futr, ghost_curr):
    """Check if the Pacman can escape from a ghost.

    Args:
        neighbor: The neighbor coordinate that the Pacman tries to move to.
        ghost_curr: The current position of each ghost
        ghost_futr: The future position of each ghost.

    Returns:
        can_move: False if the neighbor is occupied by the ghost or the Pacman must pass through the ghost to reach there.
    """
    for i in range(0, len(ghost_futr)):
        if (ghost_futr[i] == neighbor):
            return False
        elif (ghost_curr[i] == neighbor) and (ghost_futr[i] == curr):
            return False
    return True

def bfs(maze_ra, start, end):
    """Performs breadth-first search for a path through the maze.

    Args:
        maze_ra: The array populated with the maze characters.
        start: The (r,c) tuple coordinate to start from.
        end: The (r,c) tuple that the path much reach.

    Returns:
        soln_path: The path through the maze from start to end.
        int: The number of nodes visited.
        int: The cost of the solution path.
    """
    frontier = deque([]) # Queue: append(), popleft()
    visited = [start] # List of tuples representing coordinates
                      # already checked.
    paths = deque([[start]])
    curr = start
    directions = [(0,1), (1,0), (0,-1), (-1,0)]
    while curr != end:
        curr_path = paths.popleft()
        for d in directions:
            neighbor = add_tuples(curr, d)
            if is_in_bounds(maze_ra, neighbor) and can_move_to(maze_ra, neighbor) and neighbor not in visited:
                visited.append(neighbor)
                frontier.append(neighbor)
                hold_path = deque(curr_path)
                hold_path.append(neighbor)
                paths.append(hold_path)
        curr = frontier.popleft()
    soln_path = paths.popleft()
    return soln_path, len(visited), len(soln_path)

def dfs(maze_ra, start, end):
    """Performs depth-first search for a path through the maze.

    Args:
        maze_ra: The array populated with the maze characters.
        start: The (r,c) tuple coordinate to start from.
        end: The (r,c) tuple that the path much reach.

    Returns:
        soln_path: The path through the maze from start to end.
        int: The number of nodes visited.
        int: The cost of the solution path.
    """
    frontier = deque([]) # Stack: append(), popright()
    visited = [start] # List of tuples representing coordinates
                      # already checked.
    paths = deque([[start]])
    curr = start
    directions = [(0,1), (1,0), (0,-1), (-1,0)]
    while curr != end:
        curr_path = paths.pop()
        for d in directions:
            neighbor = add_tuples(curr, d)
            if is_in_bounds(maze_ra, neighbor) and can_move_to(maze_ra, neighbor) and neighbor not in visited:
                visited.append(neighbor)
                frontier.append(neighbor)
                hold_path = deque(curr_path)
                hold_path.append(neighbor)
                paths.append(hold_path)
        curr = frontier.pop()
    soln_path = paths.pop()
    return soln_path, len(visited), len(soln_path)

def manhattan_dist(curr, end):
    """Computes the Manhattan distance between current and end nodes.

    Manhattan distance is defined as the distance between two points
    if only movement along the horizontal and vertical axes are
    allowed.

    Args:
        curr: The (r,c) tuple coordinates of the current node.
        end: The (r,c) tuple coordinates of the end node.

    Returns:
        int: The Manhattan distance between the current and end nodes.
    """
    return abs(end[0] - curr[0]) + abs(end[1] - curr[1])

def alt_heuristic(curr, end, move_cost, turn_cost, curr_dir):
    """Computes the alternative heuristic between current and end nodes.

    This heuristic is computed by multiplying the forward movement
    cost by the Manhattan distance and then adding the turn
    cost. Manhattan distance is the distance between two points on a
    2D grid when taking only horizontal and vertical paths; this
    equivalent to moving horizontally until the end horizontal
    coordinate is reached, then turning and moving vertically until
    the vertical coordinate is reached. Therefore, the cost should be
    the number of steps in the path multipled by the cost of each
    step, plus the cost of one turn to transition from horizontal to
    vertical movement.

    Args:
        curr: The (r,c) tuple coordinates of the current node.
        end: The (r,c) tuple coordinates of the end node.
        move_cost: The cost of forward movement.
        turn_cost: The cost of turning.
        curr_dir: The direction Pacman is currenly facing.

    Returns:
        int: The heuristic cost between the current and end nodes.
    """
    ra = [] # Horizontal dir to go, vertical dir to go
    hori_dir = end[0] - curr[0]
    vert_dir = end[1] - curr[1]
    if hori_dir > 0:
        ra.append((0,-1))
    elif hori_dir < 0:
        ra.append((0,1))
    else:
        ra.append((0,0))
    if vert_dir > 0:
        ra.append((1,0))
    elif vert_dir < 0:
        ra.append((-1,0))
    else:
        ra.append((0,0))
    tot_turn_cost = 0
    for item in ra:
        if item == (0,0):
            continue
        tot_turn_cost += turn_cost
    return (manhattan_dist(curr, end) * move_cost) + tot_turn_cost

def greedy_bfs(maze_ra, start, end):

    """Performs greedy best-first search for a path through the maze.

    Args:
        maze_ra: The array populated with the maze characters.
        start: The (r,c) tuple coordinate to start from.
        end: The (r,c) tuple that the path much reach.

    Returns:
        soln_path: The path through the maze from start to end.
        int: The number of nodes visited.
        int: The cost of the solution path.
    """
    frontier = [(manhattan_dist(start, end), [start], start)] # Manhattan distance, path to node, node.
    visited = [start]
    curr_data = heapq.heappop(frontier)
    curr = curr_data[2] # curr = start
    directions = [(0,1), (1,0), (0,-1), (-1,0)]
    last_path = []
    while curr != end:
        curr_path = curr_data[1]
        for d in directions:
            neighbor = add_tuples(curr, d)
            if is_in_bounds(maze_ra, neighbor) and can_move_to(maze_ra, neighbor) and neighbor not in visited:
                visited.append(neighbor)
                hold_path = deque(curr_path)
                hold_path.append(neighbor)
                last_path = hold_path
                neighbor_tuple = (manhattan_dist(neighbor, end), hold_path, neighbor)
                heapq.heappush(frontier, neighbor_tuple)
        curr_data = heapq.heappop(frontier)
        curr = curr_data[2]
    # soln_path = heapq.heappop(frontier)[1]
    soln_path = curr_data[1]
    return soln_path, len(visited), len(soln_path)

def a_star(maze_ra, start, end):
    """Performs A* search for a path through the maze.

    Args:        
        maze_ra: The array populated with the maze characters.
        start: The (r,c) tuple coordinate to start from.
        end: The (r,c) tuple that the path much reach.

    Returns:
        soln_path: The path through the maze from start to end.
        int: The number of nodes visited.
        int: The cost of the solution path.
    """
    frontier = [(0 + manhattan_dist(start, end), 0, [start], start)] # Manhattan distance, path to node, node.
    visited = [start]
    curr_data = heapq.heappop(frontier)
    curr = curr_data[3] # curr = start
    directions = [(0,1), (1,0), (0,-1), (-1,0)]
    last_path = []
    while curr != end:
        curr_path = curr_data[2]
        curr_path_cost = curr_data[1]
        for d in directions:
            neighbor = add_tuples(curr, d)
            if is_in_bounds(maze_ra, neighbor) and can_move_to(maze_ra, neighbor) and neighbor not in visited:
                visited.append(neighbor)
                hold_path = deque(curr_path)
                hold_path.append(neighbor)
                last_path = hold_path
                neighbor_tuple = (curr_path_cost + 1 + manhattan_dist(neighbor, end), curr_path_cost + 1, hold_path, neighbor)
                heapq.heappush(frontier, neighbor_tuple)
        curr_data = heapq.heappop(frontier)
        curr = curr_data[3]
    soln_path = curr_data[2]
    return soln_path, len(visited), len(soln_path)

def get_turn_cost(turn_cost, curr_dir, new_dir):
    """Returns a positive turn cost if current direction is not the
    same as the one required to move.

    Args:
        turn_cost: The cost of turning.
        curr_dir: The direction Pacman is currently facing.
        new_dir: The direction Pacman needs to face to move.

    Returns:
        int: The cost of turning, if turning is
        required. Else, 0.
    """
    # if not curr_dir == new_dir:
    #     return turn_cost
    # return 0
    tuple_sum = add_tuples(curr_dir, new_dir)
    if tuple_sum == (0,0):
        return turn_cost * 2
    elif (tuple_sum == (1,1) or tuple_sum == (1,-1) or tuple_sum == (-1,-1) or tuple_sum == (-1,1)):
        return turn_cost
    else:
        return 0

def a_star_turns(maze_ra, start, end, move_cost, turn_cost, use_alt):
    """Performs A* search for a path through the maze.

    Args:        
        maze_ra: The array populated with the maze characters.
        start: The (r,c) tuple coordinate to start from.
        end: The (r,c) tuple that the path much reach.
        move_cost: The cost of forward movement.
        turn_cost: The cost of turning.
        use_alt: True to use alternate heuristic, else Manhattan used.

    Returns:
        soln_path: The path through the maze from start to end.
        int: The number of nodes visited.
        int: The cost of the solution path.
    """
    frontier = [(0 + manhattan_dist(start, end), 0, [start], start, (0,1))] # Path cost + Manhattan distance, path cost to node, path, node, direction after moving to node.
    visited = [start]
    curr_data = heapq.heappop(frontier)
    curr = curr_data[3] # curr = start
    directions = [(0,1), (1,0), (0,-1), (-1,0)]
    last_path = []
    last_cost = 0
    while curr != end:
        curr_path = curr_data[2]
        curr_path_cost = curr_data[1]
        curr_dir = curr_data[4]
        for d in directions:
            neighbor = add_tuples(curr, d)
            if is_in_bounds(maze_ra, neighbor) and can_move_to(maze_ra, neighbor) and neighbor not in visited:
                visited.append(neighbor)
                hold_path = deque(curr_path)
                hold_path.append(neighbor)
                last_path = hold_path
                last_cost = curr_path_cost + move_cost + get_turn_cost(turn_cost, curr_dir, d)
                if not use_alt:
                    neighbor_tuple = (curr_path_cost + move_cost + get_turn_cost(turn_cost, curr_dir, d) + manhattan_dist(neighbor, end), curr_path_cost + move_cost + get_turn_cost(turn_cost, curr_dir, d), hold_path, neighbor, d)
                else:
                    # neighbor_tuple = (curr_path_cost + move_cost + get_turn_cost(turn_cost, curr_dir, d) + alt_heuristic(neighbor, end, move_cost, get_turn_cost(turn_cost, curr_dir, d), curr_dir), curr_path_cost + move_cost + get_turn_cost(turn_cost, curr_dir, d), hold_path, neighbor, d)
                    neighbor_tuple = (curr_path_cost + move_cost + get_turn_cost(turn_cost, curr_dir, d) + alt_heuristic(neighbor, end, move_cost, turn_cost, curr_dir), curr_path_cost + move_cost + get_turn_cost(turn_cost, curr_dir, d), hold_path, neighbor, d)
                heapq.heappush(frontier, neighbor_tuple)
        curr_data = heapq.heappop(frontier)
        curr = curr_data[3]
    soln_path = curr_data[2]
    return soln_path, len(visited), last_cost

def a_star_ghost(maze_ra, start, end, ghost_start, ghost_initial_direction):
    """Performs A* search for a path through the maze.

    Args:        
        maze_ra: The array populated with the maze characters.
        start: The (r,c) tuple coordinate to start from.
        end: The (r,c) tuple that the path much reach.
        ghost : The (r,c) tuple coordinate of the ghost.
        ghost_direction : The (r,c) tuple direction of the ghost.

    Returns:
        soln_path: The path through the maze from start to end.
        int: The number of nodes visited.
        int: The cost of the solution path.


    Problems:
        When frointier fails and we move the frontier back to the parent, we must let the ghost be back as well.

    """
    frontier = [(0 + manhattan_dist(start, end), 0, [start], start, ghost_start, ghost_initial_direction, [ghost_start])] # Manhattan distance, path to node, node, ghost location, ghost direction.
    visited_states = [(start, ghost_start, ghost_initial_direction)]
    curr_data = heapq.heappop(frontier)
    curr = curr_data[3] # curr = start
    directions = [(0,1), (1,0), (0,-1), (-1,0)]
    while curr != end:
        curr_path = curr_data[2]
        curr_ghost_path = curr_data[6]
        curr_path_cost = curr_data[1]
        ghost_curr = curr_data[4]
        ghost_direction = curr_data[5]
        ghost_futr = []
        for i in range(0, len(ghost_direction)):
            futr, ghost_direction[i] = ghost_moves(maze_ra, ghost_curr[i], ghost_direction[i]) 
            ghost_futr.append(futr)
        for d in directions:
            neighbor = add_tuples(curr, d)
            possible_state = [(neighbor, ghost_futr, ghost_direction)]
            '''print(str(can_escape_from_ghost_to(maze_ra, neighbor, curr, ghost_futr, ghost_curr)) + "," + str(possible_state not in visited_states))
            print(possible_state)
            print(visited_states)'''
            if is_in_bounds(maze_ra, neighbor) and can_move_to(maze_ra, neighbor) and can_escape_from_ghost_to(maze_ra, neighbor, curr, ghost_futr, ghost_curr) and possible_state not in visited_states:
                visited_states.append(possible_state)
                print(curr_ghost_path)
                print(ghost_futr)
                hold_ghost_path = []
                for i in range(0, len(curr_ghost_path)):
                    ghost_curr = deque(curr_ghost_path[i])
                    ghost_curr.append(ghost_futr[i])
                    hold_ghost_path.append(ghost_curr)
                hold_path = deque(curr_path)
                hold_path.append(neighbor)
                possible_tuple = (curr_path_cost + 1 + manhattan_dist(neighbor, end), curr_path_cost + 1, hold_path, neighbor, ghost_futr, ghost_direction, hold_ghost_path)
                heapq.heappush(frontier, possible_tuple)
        curr_data = heapq.heappop(frontier)
        curr = curr_data[3]
        #print(neighbor, ghost_futr, ghost_curr, curr, ghost_curr == neighbor and ghost_futr==curr)
    soln_path = curr_data[2]
    soln_ghost_path = curr_data[6]
    return soln_path, soln_ghost_path, len(visited_states), len(soln_path)

def get_corners(maze_ra):
    # clockwise direction
    direction = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    corners = []
    for row in range(0, len(maze_ra)):
        for col in range(0, len(maze_ra[0])):
            if can_move_to(maze_ra, (row, col)):
                pre = True
                for d in direction:
                    neighbor = add_tuples((row, col), d)
                    if not can_move_to(maze_ra, neighbor):
                        if pre == False:
                            corners.append((row, col))
                            break
                    pre = can_move_to(maze_ra, neighbor)
    return corners

def eat_dot2(maze_ra, start, arr_dots):
    corners = get_corners(maze_ra)
    step = None
    current = start
    soln_path = []
    num_node = count_path_node(maze_ra)
    total_expanded = 0
    visited_map = {}
    directions = [(-1,0), (1, 0), (0,-1), (0,1)]
    while len(arr_dots) > 0:
        dist = sys.maxsize
        step = None
        target = None
        need_dijkstra = True
        for d in directions:
            neighbor = add_tuples(current, d)
            if neighbor in arr_dots:
                target = neighbor
                need_dijkstra = False
                break
        if need_dijkstra:
            if len(corners) > 0:
                select_from = corners
            else:
                select_from = arr_dots
            for dot in select_from:
                p = run_dijkstra(maze_ra, current, dot, num_node)
                if len(p) < dist:
                    dist = len(p)
                    step = p
                    target = dot
        step, expanded, cost = a_star(maze_ra, current, target)
        total_expanded += expanded
        current = target
        for i in range(1, len(step)):
            if step[i] in arr_dots:
                arr_dots.remove(step[i])
            if step[i] in corners:
                corners.remove(step[i])
            soln_path.append(step[i])
    soln_path.insert(0, start)
    return soln_path, total_expanded, len(soln_path)
    
def eat_dot1(maze_ra, start, arr_dots):
    # shortest distance to current position, dot location 
    step = None
    current = start
    soln_path = []
    num_node = count_path_node(maze_ra)
    total_expanded = 0
    eat = []
    while len(arr_dots) > 0:
        dist = sys.maxsize
        target = None
        directions = [(0,1), (1,0), (0,-1), (-1,0)]
        for d in directions:
            neighbor = add_tuples(current, d)
            if neighbor in arr_dots:
                target = neighbor
                need_dijkstra = False
                break
        need_dijkstra = True
        if need_dijkstra:
            for dot in arr_dots:
                p = run_dijkstra(maze_ra, current, dot, num_node)
                if len(p) < dist:
                    dist = len(p)
                    step = p
                    target = dot
        if target != None:
            arr_dots.remove(target)
        step, expanded, cost = a_star(maze_ra, current, target)
        total_expanded += expanded
        eat.append(target)
        current = target
        for i in range(1, len(step)):
            soln_path.append(step[i])
    soln_path.insert(0, start)
    return soln_path, num_node, len(soln_path)

def run_dijkstra(maze_ra, start, end, num_node):
    visited = []
    frontier = []
    direction = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    for row in range(0, len(maze_ra)):
        for col in range(0, len(maze_ra[0])):
            if maze_ra[row][col] != '%':
                neighbors = []
                for d in direction:
                    neighbor = add_tuples((row, col), d)
                    if can_move_to(maze_ra, neighbor):
                        neighbors.append(neighbor)
                if row == start[0] and col == start[1]:
                    heapq.heappush(frontier, (0, (row, col), neighbors))
                else:
                    heapq.heappush(frontier, (sys.maxsize, (row, col), neighbors))
    while len(visited) < num_node:
        cur = heapq.heappop(frontier)
        visited.append(cur)
        for cur_neighbor in cur[2]:
            neighbor_node = get_tuple(frontier, visited, cur_neighbor)
            if cur[0] + 1 < neighbor_node[0]:
                new_cost_neighbor = (cur[0] + 1, cur_neighbor, neighbor_node[2])
                if neighbor_node in frontier:
                    frontier.remove(neighbor_node)
                    heapq.heapify(frontier)
                    heapq.heappush(frontier, (new_cost_neighbor))
                else:
                    visited.remove(neighbor_node)
                    visited.append(new_cost_neighbor)
    path = [end]
    cur = get_tuple(frontier, visited, end)
    while cur[1] != start:
        min_dist = sys.maxsize
        for neighbor in cur[2]:
            node = get_tuple(frontier, visited, neighbor)
            if node[0] < min_dist:
                min_dist = node[0]
                cur = node
        path.insert(0, cur[1])
    path.insert(0, start)
    return path

def get_tuple(frontier, visited, item):
    for node in frontier:
        if node[1] == item:
            return node
    for node in visited:
        if node[1] == item:
            return node

def count_path_node(maze_ra):
    count = 0
    for row in range(0, len(maze_ra)):
        for col in range(0, len(maze_ra[0])):
            if maze_ra[row][col] != '%':
                count += 1
    return count

def mark_soln_path(maze_ra, path_coords):
    """Fills in the solution path with '.'

    Args:
        maze_ra: The array populated with the maze characters.
        path_coords: The deque of (r,c) tuple coordinates representing the solution path through the maze.

    Returns:
        soln_ra: The maze array with the path marked by '.'.
    """
    soln_ra = maze_ra
    is_start = True
    path_cost = 0
    for coord in path_coords:
        r_idx = coord[0]
        c_idx = coord[1]
        if soln_ra[r_idx][c_idx] != '%':
            if soln_ra[r_idx][c_idx] != 'P':
                soln_ra[r_idx][c_idx] = '.' 
            is_start = False
            if not is_start:
                path_cost = path_cost + 1
        else:
            print('Path goes through wall at (' + str(r_idx) + ',' + str(c_idx) + ').')
    return soln_ra, path_cost

def print_2d_array(maze_ra):
    """Prints a 2D array.

    Args:
        maze_ra: The array populated with the maze characters.
    """
    r_idx = c_idx = 0
    num_rows = len(maze_ra)
    num_cols = len(maze_ra[0])
    for r in maze_ra:
        hold_row = ''
        for c in r:
            hold_row += c
        print(hold_row)
        hold_row = ''
    print()

def map_search(maze_ra):
    walls = []
    r_idx = c_idx = 0
    num_rows = len(maze_ra)
    num_cols = len(maze_ra[0])
    for r in maze_ra:
        for c in r:
            if c =='%':
                walls.append((r_idx, c_idx))
            c_idx += 1
        c_idx = 0
        r_idx += 1
    return (SQUARE_SIZE * num_cols, SQUARE_SIZE * num_rows), walls

def draw_maze(screen, walls):
    for x in walls:
        square =  pygame.Rect(SQUARE_SIZE * x[1], SQUARE_SIZE * x[0], SQUARE_SIZE, SQUARE_SIZE)
        pygame.draw.rect(screen, (255, 255, 0), square) 

def draw_dots(screen, dots):
    for x in dots:
        square = pygame.Rect(SQUARE_SIZE * x[1], SQUARE_SIZE * x[0], SQUARE_SIZE, SQUARE_SIZE)
        pygame.draw.rect(screen, (0, 255, 0), square)   

def draw_position(screen, to_go, paths):
    x = to_go.pop(0)
    paths.append(x)
    center = (SQUARE_SIZE * x[1] + SQUARE_SIZE/2, SQUARE_SIZE * x[0] + SQUARE_SIZE/2)
    pygame.draw.circle(screen, (255, 100, 100), center, 3 * PATH_RADIUS)

def draw_ghost_position(screen, ghost_as_tuple_coords):
    x = ghost_as_tuple_coords.popleft()
    center = (SQUARE_SIZE * x[1] + SQUARE_SIZE/2, SQUARE_SIZE * x[0] + SQUARE_SIZE/2)
    pygame.draw.circle(screen, (255, 255, 255), center, 3 * PATH_RADIUS)

def draw_ghost(screen, maze_ra, ghost_curr, ghost_direction):
    ghost_center = (SQUARE_SIZE * ghost_curr[1] + SQUARE_SIZE/2, SQUARE_SIZE * ghost_curr[0] + SQUARE_SIZE/2)
    pygame.draw.circle(screen, (255, 255, 255), ghost_center, 3 * PATH_RADIUS)
    ghost_futr, ghost_direction_futr= ghost_moves(maze_ra, ghost_curr, ghost_direction)
    return ghost_futr, ghost_direction_futr

def draw_path(screen, paths):
    for x in paths:
        center = (SQUARE_SIZE * x[1] + SQUARE_SIZE/2, SQUARE_SIZE * x[0] + SQUARE_SIZE/2)
        pygame.draw.circle(screen, (255, 0, 0), center, PATH_RADIUS)

def animation_main(size, walls, dots, soln_as_tuple_coords, ghost_as_tuple_coords):
    to_go = soln_as_tuple_coords
    paths = []
    pygame.display.set_caption("MP1 Maze Animation")
    screen = pygame.display.set_mode(size)   
    clock = pygame.time.Clock()
    running = True
    while running:
        clock.tick(60)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False

        screen.fill((0, 0, 0))
        draw_maze(screen, walls)
        draw_dots(screen, dots)
        draw_position(screen, to_go, paths)
        if ghost_as_tuple_coords != []:
            draw_ghost_position(screen, ghost_as_tuple_coords)
        draw_path(screen, paths)
        pygame.display.flip()
        pygame.time.wait(300)
        pygame.display.flip()
        if len(to_go) == 0:
            running = False

def main():
    maze_file, alg, move_cost, turn_cost = parse_cl_args()
    maze_rows = read_file(maze_file)
    if alg[:6] == 'eatdot':
        maze_ra, start, dots, ghost_start, walls = create_maze_array(maze_rows, True)
    else:
        maze_ra, start, dots, ghost_start, walls = create_maze_array(maze_rows, False)
        end = dots[-1]
    size = (SQUARE_SIZE * len(maze_ra[0]), SQUARE_SIZE * len(maze_ra))
    # # For ../data/smallTurns.txt.
    # # Check maze_ra correctly represents maze from file.
    # for r in maze_ra:
    #     hold_row = ''
    #     for c in r:
    #         hold_row += c
    #     print(hold_row)
    # # Check start and end points are correct.
    # print('Start point: ' + str(start))
    # print('End point: ' + str(end))
    # # Check bounds check is correct.
    # print('(0,0): ' + str(is_in_bounds(maze_ra, (0,0))))
    # print('(-1,-1): ' + str(is_in_bounds(maze_ra, (-1,-1))))
    # print('(-1,0): ' + str(is_in_bounds(maze_ra, (-1,0))))
    # print('(0,-1): ' + str(is_in_bounds(maze_ra, (0,-1))))
    # print('(1,2): ' + str(is_in_bounds(maze_ra, (1,2))))
    # print('(34,20): ' + str(is_in_bounds(maze_ra, (34,20))))
    # # Check identifying maze walls correctly.
    # print('At (0,5): ' + str(can_move_to(maze_ra, (0,5))))
    # print('At (1,11): ' + str(can_move_to(maze_ra, (1,11))))
    # print('At (34,20): ' + str(can_move_to(maze_ra, (34,20))))
    # print('At (9,30): ' + str(can_move_to(maze_ra, (9,30))))
    # print('At (1,30): ' + str(can_move_to(maze_ra, (1,30))))

    # Start search algorithms.
    soln_as_tuple_coords = deque([])
    ghost_as_tuple_coords = []
    num_nodes_visited = 0
    path_cost = 0
    if alg == 'bfs':
        soln_as_tuple_coords, num_nodes_visited, path_cost = bfs(maze_ra, start, end)
    elif alg == 'dfs':
        soln_as_tuple_coords, num_nodes_visited, path_cost = dfs(maze_ra, start, end)
    elif alg == 'greedy':
        soln_as_tuple_coords, num_nodes_visited, path_cost = greedy_bfs(maze_ra, start, end)
    elif alg == 'astar' or (alg == 'astarghost' and ghost_start == None):
        soln_as_tuple_coords, num_nodes_visited, path_cost = a_star(maze_ra, start, end)
    elif alg == 'turns':
        soln_as_tuple_coords, num_nodes_visited, path_cost = a_star_turns(maze_ra, start, end, move_cost, turn_cost, False)
    elif alg == 'alt':
        soln_as_tuple_coords, num_nodes_visited, path_cost = a_star_turns(maze_ra, start, end, move_cost, turn_cost, True)
    elif alg == 'astarghost':
        ghost_init_direction = []
        for i in range(0, len(ghost_start)):
            ghost_init_direction.append((0,1))
        soln_as_tuple_coords, ghost_as_tuple_coords, num_nodes_visited, path_cost = a_star_ghost(maze_ra, start, end, ghost_start, ghost_init_direction)
    elif alg == 'eatdot1':
        soln_as_tuple_coords, num_nodes_visited, path_cost = eat_dot1(maze_ra, start, dots)
    elif alg == 'eatdot2':
        soln_as_tuple_coords, num_nodes_visited, path_cost = eat_dot2(maze_ra, start, dots)
    to_go = list(soln_as_tuple_coords)
    #animation_main(size, walls, dots, to_go, ghost_as_tuple_coords)
    soln_ra, path_cost = mark_soln_path(maze_ra, soln_as_tuple_coords)
    print('Path cost: ' + str(path_cost))
    print('Number of nodes expanded: ' + str(num_nodes_visited))
    print_2d_array(soln_ra)


if __name__ == '__main__':
    main()
