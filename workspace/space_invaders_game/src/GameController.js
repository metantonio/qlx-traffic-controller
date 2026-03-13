import React, { useEffect } from 'react';
import Player from './Player';
import Enemies from './Enemies';

const GameController = () => {
  useEffect(() => {
    // Game loop logic here
    return () => {
      // Cleanup logic here
    };
  }, []);

  return (
    <div id="game-controller">
      <Player />
      <Enemies />
    </div>
  );
};

export default GameController;
