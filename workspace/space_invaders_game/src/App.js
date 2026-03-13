import React from 'react';
import './App.css';
import GameBoard from './GameBoard';
import Player from './Player';
import Enemies from './Enemies';
import Bullets from './Bullets';

function App() {
  return (
    <div className="App">
      <h1>Space Invaders Game</h1>
      <GameBoard>
        <Player />
        <Enemies />
        <Bullets />
      </GameBoard>
    </div>
  );
}

export default App;