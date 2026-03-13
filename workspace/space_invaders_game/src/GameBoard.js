import React from 'react';
import Player from './Player';
import Enemies from './Enemies';
import Scoreboard from './Scoreboard';
import GameController from './GameController';

const GameBoard = () => {
  return (
    <div id="game-board">
      <GameController />
      <Player />
      <Enemies />
      <Scoreboard />
    </div>
  );
};

export default GameBoard;
