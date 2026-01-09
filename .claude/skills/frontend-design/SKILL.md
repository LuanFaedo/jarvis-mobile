---
name: frontend-design
description: Design and implement frontend UI components, layouts, and user interfaces. Use when building web interfaces, React components, designing layouts, implementing responsive design, working with CSS/Tailwind, or improving UI/UX. Includes accessibility, mobile-first design, and component architecture best practices.
---

# Frontend Design

A comprehensive skill for designing and implementing modern frontend user interfaces with best practices for accessibility, responsiveness, and maintainability.

## When to Use This Skill

Use this skill when:
- Designing new UI components or layouts
- Implementing responsive designs
- Working with React, Vue, or other component frameworks
- Styling with CSS, Tailwind, or CSS-in-JS
- Improving accessibility (a11y)
- Refactoring frontend code
- Creating design systems or component libraries

## Core Principles

### 1. Mobile-First Responsive Design

Always start with mobile viewport and progressively enhance:

```css
/* Mobile first (default) */
.container {
  padding: 1rem;
  width: 100%;
}

/* Tablet and up */
@media (min-width: 768px) {
  .container {
    padding: 2rem;
    max-width: 768px;
  }
}

/* Desktop and up */
@media (min-width: 1024px) {
  .container {
    padding: 3rem;
    max-width: 1200px;
  }
}
```

**Tailwind equivalent**:
```jsx
<div className="w-full p-4 md:p-8 lg:max-w-6xl lg:p-12">
```

### 2. Accessibility (WCAG 2.1 AA Standards)

#### Semantic HTML
```jsx
// Good - semantic and accessible
<nav aria-label="Main navigation">
  <ul>
    <li><a href="/home">Home</a></li>
  </ul>
</nav>

// Bad - not semantic
<div className="nav">
  <div onClick={goHome}>Home</div>
</div>
```

#### ARIA Labels and Roles
```jsx
<button aria-label="Close dialog" onClick={handleClose}>
  <XIcon aria-hidden="true" />
</button>

<input
  type="text"
  id="email"
  aria-describedby="email-hint"
  aria-invalid={errors.email ? "true" : "false"}
/>
<span id="email-hint">We'll never share your email</span>
```

#### Keyboard Navigation
Ensure all interactive elements are keyboard accessible (Tab, Enter, Space, Escape).

#### Color Contrast
- Normal text: 4.5:1 contrast ratio minimum
- Large text (18pt+): 3:1 contrast ratio minimum
- Use tools like WebAIM Contrast Checker

### 3. Component Architecture

#### Atomic Design Pattern

Organize components hierarchically:

```
components/
├── atoms/          # Basic building blocks (Button, Input, Label)
├── molecules/      # Simple combinations (FormField, SearchBar)
├── organisms/      # Complex components (Header, ProductCard)
├── templates/      # Page layouts
└── pages/          # Specific page instances
```

#### Component Best Practices

```jsx
// Good - Single Responsibility, Composable, Accessible
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  onClick,
  type = 'button',
  className = '',
  ...props
}) {
  const baseStyles = 'font-semibold rounded transition-colors focus:outline-none focus:ring-2';
  const variantStyles = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500',
    outline: 'border-2 border-gray-300 hover:border-gray-400 focus:ring-gray-400'
  };
  const sizeStyles = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg'
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className} disabled:opacity-50 disabled:cursor-not-allowed`}
      {...props}
    >
      {children}
    </button>
  );
}
```

### 4. Layout Patterns

#### Flexbox for 1D Layouts
```css
/* Center content */
.flex-center {
  display: flex;
  justify-content: center;
  align-items: center;
}

/* Space between items */
.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
```

#### Grid for 2D Layouts
```css
/* Responsive grid */
.grid-responsive {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

/* Named grid areas */
.layout {
  display: grid;
  grid-template-areas:
    "header header"
    "sidebar main"
    "footer footer";
  grid-template-columns: 250px 1fr;
  gap: 1rem;
}
```

### 5. Color Systems

Define a consistent color palette:

```js
// Design tokens
const colors = {
  primary: {
    50: '#eff6ff',
    100: '#dbeafe',
    500: '#3b82f6',
    600: '#2563eb',
    900: '#1e3a8a'
  },
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    500: '#6b7280',
    900: '#111827'
  },
  // semantic colors
  success: '#10b981',
  error: '#ef4444',
  warning: '#f59e0b',
  info: '#3b82f6'
};
```

### 6. Typography Scale

```css
/* Type scale (1.25 ratio) */
.text-xs { font-size: 0.75rem; }    /* 12px */
.text-sm { font-size: 0.875rem; }   /* 14px */
.text-base { font-size: 1rem; }     /* 16px */
.text-lg { font-size: 1.25rem; }    /* 20px */
.text-xl { font-size: 1.5rem; }     /* 24px */
.text-2xl { font-size: 1.875rem; }  /* 30px */
.text-3xl { font-size: 2.25rem; }   /* 36px */

/* Line heights */
.leading-tight { line-height: 1.25; }
.leading-normal { line-height: 1.5; }
.leading-relaxed { line-height: 1.75; }
```

### 7. Spacing System

Use consistent spacing scale (usually 4px or 8px base):

```js
// 4px base scale
const spacing = {
  0: '0',
  1: '0.25rem',  // 4px
  2: '0.5rem',   // 8px
  3: '0.75rem',  // 12px
  4: '1rem',     // 16px
  6: '1.5rem',   // 24px
  8: '2rem',     // 32px
  12: '3rem',    // 48px
  16: '4rem'     // 64px
};
```

## Common UI Patterns

### Loading States

```jsx
function LoadingSpinner({ size = 'md' }) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  };

  return (
    <div className={`${sizeClasses[size]} border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin`} role="status">
      <span className="sr-only">Loading...</span>
    </div>
  );
}
```

### Form Validation

```jsx
function FormField({ label, error, required, children }) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500 ml-1" aria-label="required">*</span>}
      </label>
      {children}
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
```

### Modal/Dialog

```jsx
function Modal({ isOpen, onClose, title, children }) {
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <h2 id="modal-title" className="text-xl font-bold mb-4">
          {title}
        </h2>
        {children}
      </div>
    </div>
  );
}
```

### Dropdown Menu

```jsx
function Dropdown({ trigger, items }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useClickOutside(dropdownRef, () => setIsOpen(false));

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {trigger}
      </button>

      {isOpen && (
        <ul
          className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5"
          role="menu"
        >
          {items.map((item, index) => (
            <li key={index}>
              <button
                className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                role="menuitem"
                onClick={() => {
                  item.onClick();
                  setIsOpen(false);
                }}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

## Performance Optimization

### Image Optimization

```jsx
// Use Next.js Image component or similar
<Image
  src="/hero.jpg"
  alt="Hero image"
  width={1200}
  height={600}
  loading="lazy"
  placeholder="blur"
/>

// Native lazy loading
<img
  src="image.jpg"
  alt="Description"
  loading="lazy"
  decoding="async"
/>
```

### Code Splitting

```jsx
// React lazy loading
const HeavyComponent = lazy(() => import('./HeavyComponent'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <HeavyComponent />
    </Suspense>
  );
}
```

### CSS Optimization

- Avoid deeply nested selectors
- Use CSS custom properties for theming
- Minimize specificity conflicts
- Consider CSS-in-JS for component-scoped styles

## Design Checklist

Before considering a component complete:

- [ ] Responsive across mobile, tablet, desktop
- [ ] Keyboard accessible (Tab, Enter, Escape navigation)
- [ ] Screen reader friendly (ARIA labels, semantic HTML)
- [ ] Sufficient color contrast (4.5:1 for text)
- [ ] Loading and error states handled
- [ ] Focus states visible
- [ ] Touch targets at least 44x44px (mobile)
- [ ] Animations respect prefers-reduced-motion
- [ ] Works without JavaScript (progressive enhancement)
- [ ] Cross-browser tested

## Tools and Resources

- **Design**: Figma, Sketch, Adobe XD
- **Accessibility**: axe DevTools, WAVE, Lighthouse
- **Color**: Coolors, Adobe Color, contrast checkers
- **Icons**: Heroicons, Lucide, Font Awesome
- **Inspiration**: Dribbble, Behance, Awwwards

## Example Workflow

1. **Understand requirements** - What problem does this UI solve?
2. **Research patterns** - How do other apps solve this?
3. **Sketch wireframes** - Low-fidelity layout ideas
4. **Define component structure** - Break down into reusable pieces
5. **Implement mobile-first** - Start with smallest viewport
6. **Add interactivity** - Forms, buttons, animations
7. **Test accessibility** - Screen reader, keyboard, contrast
8. **Optimize performance** - Lazy load, optimize images
9. **Cross-browser test** - Chrome, Firefox, Safari, Edge

## Anti-Patterns to Avoid

- Using `div` for everything (use semantic HTML)
- Inline styles everywhere (use CSS classes or CSS-in-JS)
- Fixed pixel widths (use relative units: rem, %, vw)
- Inaccessible color-only indicators (use icons + text)
- Non-responsive designs (always design mobile-first)
- Overusing `!important` (fix specificity instead)
- Blocking main thread with heavy animations
- Forgetting focus states for keyboard users
