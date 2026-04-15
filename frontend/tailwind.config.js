export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Playfair Display"', 'serif'],
        body:    ['"Plus Jakarta Sans"', 'sans-serif'],
      },
      colors: {
        cream: '#f5f7f5',
        teal: {
          DEFAULT: '#0d9488',
          light:   '#14b8a6',
          pale:    '#f0fdfb',
          border:  '#b2e8e0',
          mid:     '#5eead4',
        },
        ink:    { DEFAULT: '#0f2d2a', 2: '#1a4038' },
        muted:  '#5a7a72',
        border: '#ddeae7',
      },
      boxShadow: {
        sm:  '0 1px 4px rgba(13,148,136,0.08)',
        md:  '0 4px 20px rgba(13,148,136,0.12)',
        lg:  '0 8px 40px rgba(13,148,136,0.14)',
        btn: '0 6px 24px rgba(13,148,136,0.35)',
      },
      borderRadius: { xl2: '14px' },
      animation: {
        'fade-slide': 'fadeSlide 0.35s ease both',
        'rise':       'riseIn 0.5s ease both',
      },
      keyframes: {
        fadeSlide: { from: { opacity: 0, transform: 'translateY(10px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        riseIn:    { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}