import React, { useState, useEffect } from 'react';

const Enemies = () => {
  const [enemies, setEnemies] = useState([
    { x: 100, y: 50 },
    { x: 200, y: 50 },
    { x: 300, y: 50 },
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      setEnemies(prevEnemies => prevEnemies.map(enemy => ({
        ...enemy,
        y: enemy.y + 5,
      })));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      {enemies.map((enemy, index) => (
        <div
          key={index}
          id="enemy"
          style={{
            position: 'absolute',
            left: enemy.x,
            top: enemy.y,
            width: 50,
            height: 30,
            backgroundColor: 'red',
          }}
        ></div>
      ))}
    </div>
  );
};

export default Enemies;
