```typescript
import React, { useEffect, useState } from 'react';

function Home() {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setReducedMotion(reducedMotion);

    const handleReducedMotion = (e) => {
      setReducedMotion(e.matches);
    };

    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', handleReducedMotion);

    return () => {
      window.matchMedia('(prefers-reduced-motion: reduce)')..removeEventListener('change', handleReducedMotion);
    };
  }, []);

  return (
    <div className={`app ${reducedMotion ? 'reduced-motion' : ''}`}>
      {/* Other components... */}
      <h1>Welcome to Parabola</h1>
      <p className="hero-text">Transform your development workflow with our powerful tools.</p>
      <button 
        className="cta-button"
        onClick={() => {
          // CTA action
        }}
        tabIndex={0}
        aria-label="Get Started"
      >
        Get Started
      </button>
      {/* Other components... */}
    </div>
  );
}

export default Home;
```

```css
/* Add to global styles */
@media (prefers-reduced-motion: reduce) {
  .reduced-motion .hero-animation {
    animation: none;
  }
  .reduced-motion .cta-button {
    transition: none;
  }
}

/* Focus styles */
button:focus {
  outline: 2px solid #blue;
  outline-offset: 2px;
}

/* Color contrast */
body {
  color: #404040;
}

/* Decorative images */
img[alt=" decorative"] {
  alt: "";
  opacity: 0.8;
}

/* Heading structure */
h1 {
  font-size: 2rem;
  margin-bottom: 1rem;
}
```

```typescript
import React from 'react';
import { useIntl } from 'react-intl';

function Hero() {
  const { formatMessage } = useIntl();

  return (
    <div className="hero">
      <h2 className="hero-heading">
        Transform your development workflow with our powerful tools.
      </h2>
      <p className="hero-subheading">
        Streamline your workflow with our all-in-one solution for developers.
      </p>
    </div>
  );
}

export default Hero;
```

```typescript
import React from 'react';

function CTA() {
  return (
    <div className="cta-section">
      <button className="primary-button">
        Get Started
      </button>
    </div>
  );
}

export default CTA;
```