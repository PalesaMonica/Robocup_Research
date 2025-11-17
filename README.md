## Robocup Research Project
### Collaborative Perception in RoboCup 3D Soccer Simulation

This research project investigates collaborative perception strategies for the RoboCup 3D Soccer Simulation League. The system enables agents to share and integrate perception data through inter-agent communication, using a voting-based consensus mechanism to establish a unified understanding of the ball's location on the field

---

#### Overview
In multi-agent robotic soccer, individual agents have limited and potentially noisy perceptual information. This project addresses the challenge of combining observations from multiple agents to achieve more accurate and robust ball tracking through collaborative perception.

#### Research Focus

- Multi-agent ball localization through distributed sensing and communication
- Consensus-based perception fusion using voting mechanisms
- Communication protocols optimized for the RoboCup 3D environment
- Integration strategies for shared perception in team coordination

---
#### Key Features

- Collaborative Ball Perception: Agents share visual observations to collectively track the ball
- Voting-based Consensus System: Robust aggregation of perception data from multiple agents
- Round-Robin Communication Strategy: Structured agent-to-agent information exchange
- FCPCodebase Foundation: Built upon the proven FCPCodebase framework [FCPCodebase](https://github.com/m-abr/FCPCodebase?tab=readme-ov-file)

---

### Technical Approach 
#### Perception Sharing Protocol
Each agent contributes its local ball observations to the team's shared perception model. The system aggregates these observations through a voting mechanism that weights contributions based on:

- Observation confidence
- Agent proximity to the ball
- Temporal consistency of observations

#### Communication Architecture
The Round-Robin communication strategy ensures:

- Efficient bandwidth utilization
- Fair distribution of communication opportunities
- Timely propagation of critical perception updates
#### Project Structure

```graphql
├── FCPCodebase-main/
│   ├── agent_logs/          # Agents communication logs
│   ├── communication/       # Agent communication protocols  and voting algorithms       
```
### Research Context
This work explores how collaborative perception can enhance team coordination in the RoboCup 3D Soccer Simulation League. By enabling agents to share and fuse perceptual information, teams can achieve more accurate world models and make better collective decisions.
### Acknowledgments
- Built on the FCPCodebase framework

