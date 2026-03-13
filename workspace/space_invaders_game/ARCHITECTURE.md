# ARCHITECTURE.md

## Architecture Overview

### Clean Architecture

- **Use Cases**: Separate business logic from infrastructure.
- **Entities**: Represent the core concepts of the game (PlayerShip, EnemyShip, Bullet).
- **Repository**: Abstract data access layer.
- **Infrastructure**: External services and utilities (e.g., collision detection, scoring).

### Components

1. **PlayerShip Component**
   - Responsibilities: Handle player movement and shooting.
   - Dependencies: None.

2. **EnemyShip Component**
   - Responsibilities: Handle enemy movement and shooting.
   - Dependencies: None.

3. **Bullet Component**
   - Responsibilities: Handle bullet movement.
   - Dependencies: None.

4. **GameLoop Component**
   - Responsibilities: Manage game state and update logic.
   - Dependencies: PlayerShip, EnemyShip, Bullet.

5. **Collision Detection Component**
   - Responsibilities: Detect collisions between entities.
   - Dependencies: PlayerShip, EnemyShip, Bullet.

6. **Scoring and Lives Component**
   - Responsibilities: Manage scoring and lives.
   - Dependencies: None.

---

Please review the above project plan and architecture. If approved, I will proceed with the next steps.