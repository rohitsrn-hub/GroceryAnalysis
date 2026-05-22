/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
  	extend: {
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			},
  			sandy: {
  				"surface-variant": "#d3e4fe",
  				"surface-container-lowest": "#ffffff",
  				"secondary-fixed": "#eaddff",
  				"tertiary-fixed-dim": "#ffb0cd",
  				"secondary-container": "#8a4cfc",
  				"surface-container-highest": "#d3e4fe",
  				"surface-container-high": "#dce9ff",
  				"on-primary-container": "#dad7ff",
  				"secondary": "#712ae2",
  				"primary-container": "#4f46e5",
  				"surface": "#f8f9ff",
  				"inverse-on-surface": "#eaf1ff",
  				"surface-container-low": "#eff4ff",
  				"on-primary": "#ffffff",
  				"on-secondary-container": "#fffbff",
  				"outline": "#777587",
  				"primary-fixed-dim": "#c3c0ff",
  				"on-error-container": "#93000a",
  				"inverse-primary": "#c3c0ff",
  				"outline-variant": "#c7c4d8",
  				"error": "#ba1a1a",
  				"on-secondary-fixed-variant": "#5a00c6",
  				"primary": "#3525cd",
  				"on-secondary-fixed": "#25005a",
  				"primary-fixed": "#e2dfff",
  				"on-tertiary": "#ffffff",
  				"on-tertiary-container": "#ffcede",
  				"surface-container": "#e5eeff",
  				"on-surface": "#0b1c30",
  				"inverse-surface": "#213145",
  				"background": "#f8f9ff",
  				"tertiary-container": "#b6166f",
  				"secondary-fixed-dim": "#d2bbff",
  				"on-primary-fixed-variant": "#3323cc",
  				"on-background": "#0b1c30",
  				"on-secondary": "#ffffff",
  				"on-error": "#ffffff",
  				"on-tertiary-fixed-variant": "#8c0053",
  				"surface-tint": "#4d44e3",
  				"error-container": "#ffdad6",
  				"surface-dim": "#cbdbf5",
  				"on-surface-variant": "#464555",
  				"tertiary": "#8f0055",
  				"tertiary-fixed": "#ffd9e4",
  				"on-tertiary-fixed": "#3e0022",
  				"surface-bright": "#f8f9ff",
  				"on-primary-fixed": "#0f0069"
  			}
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};