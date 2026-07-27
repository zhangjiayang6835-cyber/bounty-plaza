/**
 * Dodge Roll System - Main Export
 */

const DodgeRoll = require('./mechanics/dodgeRoll');
const DodgeRollComponent = require('./components/DodgeRollComponent');
const DodgeRollInputHandler = require('./input/DodgeRollInputHandler');

module.exports = {
  DodgeRoll,
  DodgeRollComponent,
  DodgeRollInputHandler
};
