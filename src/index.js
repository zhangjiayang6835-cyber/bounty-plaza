/**
 * Dodge Roll System - Main Export
 */

const DodgeRoll = require('./mechanics/dodgeRoll');
const DodgeRollComponent = require('./components/DodgeRollComponent');

module.exports = {
  DodgeRoll,
  DodgeRollComponent,
  version: '1.0.0'
};
