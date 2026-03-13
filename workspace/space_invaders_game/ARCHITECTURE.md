# Architecture Overview: Space Invaders Game

## Overview
The game will be built using React, with a focus on clean architecture and separation of concerns.

## Components
1. **GameBoard**: Displays the game board and handles the layout.
2. **Player**: Represents the player's spaceship and controls its movement.
3. **Enemies**: Represents the enemy ships and handles their movement and shooting.
4. **Laser**: Handles the player's laser shots.
5. **Scoreboard**: Displays the player's score and lives.
6. **GameController**: Manages the game state, including game loop, scoring, and collisions.

## Dependencies
- React for the user interface.
- Axios for making HTTP requests (if needed for any external data).

## Directory Structure