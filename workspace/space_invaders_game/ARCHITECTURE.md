### Architecture Overview
The game architecture will be based on Clean Architecture and Domain-Driven Design principles to ensure separation of concerns and maintainability.

### Layers
1. **Presentation Layer (Frontend)**
   - Handles user interface and user input.
2. **Application Layer (Backend)**
   - Manages business logic and interaction with the presentation layer.
3. **Infrastructure Layer (Backend)**
   - Handles database and other external services.

### Components
1. **PlayerShip**
   - Part of the Presentation Layer.
2. **EnemyShips**
   - Part of the Presentation Layer.
3. **Bullet**
   - Part of the Presentation Layer.
4. **GameLogic**
   - Part of the Application Layer.
5. **Database**
   - Part of the Infrastructure Layer.

### Dependencies
- Presentation Layer -> Application Layer
- Application Layer -> Infrastructure Layer