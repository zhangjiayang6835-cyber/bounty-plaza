/**
 * The Universe
 * Implements the entire universe in OmniBlocks
 */
class Universe {
  constructor() {
    this.galaxies = [];
    this.blackHoles = [];
    this.darkMatter = null;
    this.initialize();
  }

  initialize() {
    // Create the observable universe
    this.createGalaxies();
    this.createStars();
    this.createPlanets();
    this.createLife();
  }

  createGalaxies() {
    // Milky Way and other galaxies
    this.galaxies = [
      { name: 'Milky Way', type: 'spiral', stars: 100000000000 },
      { name: 'Andromeda', type: 'spiral', stars: 1000000000000 },
      { name: 'Triangulum', type: 'spiral', stars: 40000000000 },
      { name: 'Whirlpool', type: 'spiral', stars: 160000000000 },
      { name: 'Sombrero', type: 'spiral', stars: 800000000000 }
    ];
  }

  createStars() {
    // Create stars in each galaxy
    this.galaxies.forEach(galaxy => {
      galaxy.stars = [];
      for (let i = 0; i < galaxy.starsCount; i++) {
        galaxy.stars.push({
          name: `Star-${i}`,
          type: this.getStarType(),
          mass: this.getStarMass(),
          temperature: this.getStarTemperature()
        });
      }
    });
  }

  createPlanets() {
    // Create planets around stars
    this.galaxies.forEach(galaxy => {
      galaxy.stars.forEach(star => {
        star.planets = [];
        const planetCount = Math.floor(Math.random() * 10) + 1;
        for (let i = 0; i < planetCount; i++) {
          star.planets.push({
            name: `Planet-${i}`,
            type: this.getPlanetType(),
            mass: this.getPlanetMass(),
            atmosphere: this.getAtmosphere(),
            life: Math.random() > 0.7 ? this.createLife() : null
          });
        }
      });
    });
  }

  createLife() {
    // Create various forms of life
    return {
      type: Math.random() > 0.5 ? 'carbon-based' : 'silicon-based',
      complexity: Math.random(),
      intelligence: Math.random() > 0.3,
      civilizations: Math.random() > 0.8 ? this.createCivilizations() : []
    };
  }

  createCivilizations() {
    // Create advanced civilizations
    return [
      {
        name: 'Ancient Empire',
        type: 'Type I',
        technology: this.getTechnologyLevel(),
        history: this.generateHistory()
      },
      {
        name: 'Federation',
        type: 'Type II',
        technology: this.getTechnologyLevel(),
        history: this.generateHistory()
      }
    ];
  }

  getStarType() {
    const types = ['Red Dwarf', 'Yellow Dwarf', 'Blue Giant', 'White Dwarf', 'Neutron Star'];
    return types[Math.floor(Math.random() * types.length)];
  }

  getStarMass() {
    return Math.random() * 100 + 0.1; // Solar masses
  }

  getStarTemperature() {
    return Math.floor(Math.random() * 30000) + 3000; // Kelvin
  }

  getPlanetType() {
    const types = ['Terrestrial', 'Gas Giant', 'Ice Giant', 'Dwarf Planet', 'Super Earth'];
    return types[Math.floor(Math.random() * types.length)];
  }

  getPlanetMass() {
    return Math.random() * 10 + 0.001; // Earth masses
  }

  getAtmosphere() {
    const atmospheres = ['Nitrogen-Oxygen', 'Methane', 'Carbon Dioxide', 'Hydrogen', 'No Atmosphere'];
    return atmospheres[Math.floor(Math.random() * atmospheres.length)];
  }

  getTechnologyLevel() {
    const levels = ['Primitive', 'Industrial', 'Atomic', 'Interstellar', 'Galactic'];
    return levels[Math.floor(Math.random() * levels.length)];
  }

  generateHistory() {
    const events = [
      'Formation of the first colony',
      'Great technological advancement',
      'Interstellar war',
      'First contact with alien species',
      'Achievement of immortality',
      'Dimensional exploration',
      'Heat death of their star'
    ];
    return events.sort(() => 0.5 - Math.random()).slice(0, 3);
  }

  expand() {
    // Universe expansion
    this.galaxies.forEach(galaxy => {
      galaxy.stars.forEach(star => {
        if (star.planets) {
          star.planets.forEach(planet => {
            if (planet.life && planet.life.civilizations) {
              planet.life.civilizations.forEach(civ => {
                civ.technology = this.getTechnologyLevel();
              });
            }
          });
        }
      });
    });
  }

  getStats() {
    return {
      galaxies: this.galaxies.length,
      totalStars: this.galaxies.reduce((sum, galaxy) => sum + galaxy.stars.length, 0),
      totalPlanets: this.galaxies.reduce((sum, galaxy) => 
        sum + galaxy.stars.reduce((starSum, star) => starSum + (star.planets ? star.planets.length : 0), 0), 0
      ),
      totalCivilizations: this.galaxies.reduce((sum, galaxy) => 
        sum + galaxy.stars.reduce((starSum, star) => 
          starSum + (star.planets ? 
            star.planets.reduce((planetSum, planet) => 
              planetSum + (planet.life && planet.life.civilizations ? planet.life.civilizations.length : 0), 0) : 0), 0), 0
      )
    };
  }
}

// Export the Universe class
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Universe;
}

// Create a new universe instance
const universe = new Universe();
console.log('Universe created with stats:', universe.getStats());

// Export the instance for OmniBlocks
window.Universe = Universe;
window.universe = universe;