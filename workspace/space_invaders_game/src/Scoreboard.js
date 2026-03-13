import React, { useState } from 'react';

const Scoreboard = () => {
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(3);

  return (
    <div id="scoreboard">
      <div>Score: {score}</div>
      <div>Lives: {lives}</div>
    </div>
  );
};

export default Scoreboard;
