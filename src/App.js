import React from 'react';
import LinuxEmulator from './components/LinuxEmulator';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>OmniBlocks Linux Emulator</h1>
        <p>Implementing Linux emulator for the $9,740,486 bounty</p>
      </header>
      <main className="App-main">
        <LinuxEmulator />
      </main>
    </div>
  );
}

export default App;