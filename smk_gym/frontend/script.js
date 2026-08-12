// Navbar Scroll Effect
window.addEventListener('scroll', () => {
    const navbar = document.getElementById('navbar');
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

// Intersection Observer for Animations
const scrollElements = document.querySelectorAll('[data-scroll]');

const elementInView = (el, dividend = 1) => {
    const elementTop = el.getBoundingClientRect().top;
    return (elementTop <= (window.innerHeight || document.documentElement.clientHeight) / dividend);
};

const displayScrollElement = (element) => {
    element.classList.add('scrolled-in');
};

const handleScrollAnimation = () => {
    scrollElements.forEach((el) => {
        if (elementInView(el, 1.25)) {
            displayScrollElement(el);
        }
    });
};

window.addEventListener('scroll', () => {
    handleScrollAnimation();
});
handleScrollAnimation();

// BMI Calculator Logic
const bmiForm = document.getElementById('bmi-form');
const bmiResult = document.getElementById('bmi-result');

bmiForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const height = document.getElementById('height').value;
    const weight = document.getElementById('weight').value;
    const btn = document.getElementById('btn-bmi');
    btn.innerHTML = 'Calculating...';

    try {
        const response = await fetch('http://localhost:8000/api/bmi', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ height, weight })
        });
        const data = await response.json();
        
        bmiResult.classList.remove('hidden');
        if (data.status === 'success') {
            bmiResult.innerHTML = `BMI: <span>${data.bmi}</span> | ${data.message}`;
            bmiResult.style.color = '#f95700';
            bmiResult.style.border = '1px solid #f95700';
        } else {
            bmiResult.innerHTML = data.error;
            bmiResult.style.color = '#e74c3c';
        }
    } catch (err) {
        bmiResult.classList.remove('hidden');
        bmiResult.innerHTML = 'Unable to connect to the server.';
    } finally {
        btn.innerHTML = 'Calculate';
    }
});

// Contact Form Logic
const contactForm = document.getElementById('contact-form');
const contactStatus = document.getElementById('contact-status');

contactForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const message = document.getElementById('message').value;
    const btn = document.getElementById('submit-contact');
    btn.innerHTML = 'Sending...';

    try {
        const response = await fetch('http://localhost:8000/api/contact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, message })
        });
        const data = await response.json();
        
        contactStatus.classList.remove('hidden');
        if (data.status === 'success') {
            contactStatus.innerHTML = data.message;
            contactStatus.style.color = '#2ecc71';
            contactForm.reset();
        } else {
            contactStatus.innerHTML = 'Something went wrong.';
            contactStatus.style.color = '#e74c3c';
        }
    } catch (err) {
        contactStatus.classList.remove('hidden');
        contactStatus.innerHTML = 'Server connection failed.';
        contactStatus.style.color = '#e74c3c';
    } finally {
        setTimeout(() => {
            contactStatus.classList.add('hidden');
        }, 5000);
        btn.innerHTML = 'Send Message';
    }
});
