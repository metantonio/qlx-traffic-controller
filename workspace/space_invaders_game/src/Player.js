import React, { useState, useEffect } from 'react';

const Player = () => {
  const [position, setPosition] = useState({ x: 50, y: 400 });

  const moveLeft = () => {
    setPosition(prevPosition => ({ ...prevPosition, x: Math.max(0, prevPosition.x - 5) }));
  };

  const moveRight = () => {
    setPosition(prevPosition => ({ ...prevPosition, x: Math.min(700, prevPosition.x + 5) }));
  };

  useEffect(() => {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') moveLeft();
      if (e.key === 'ArrowRight') moveRight();
    });

    return () => {
      document.removeEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') moveLeft();
        if (e.key === 'ArrowRight') moveRight();
      });
    };
  }, []);

  return (
    <div
      id="player"
      style={{
        position: 'absolute',
        left: position.x,
        top: position.y,
        width: 50,
        height: 30,
        backgroundColor: 'blue',
      }}
    ></div>
  );
};

export default Player;
