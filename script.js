/**
 * Автосалон PRO - Презентационный сайт
 * Основной JavaScript файл
 */

document.addEventListener('DOMContentLoaded', function() {
    // Элементы DOM
    const header = document.getElementById('header');
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    const navLinks = document.querySelectorAll('.nav-link');

    /**
     * Эффект хедера при скролле
     */
    function handleScroll() {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    }

    window.addEventListener('scroll', handleScroll);
    handleScroll(); // Проверка при загрузке

    /**
     * Мобильное меню
     */
    navToggle.addEventListener('click', function() {
        navMenu.classList.toggle('active');
        navToggle.classList.toggle('active');
    });

    // Закрытие меню при клике на ссылку
    navLinks.forEach(function(link) {
        link.addEventListener('click', function() {
            navMenu.classList.remove('active');
            navToggle.classList.remove('active');
        });
    });

    // Закрытие меню при клике вне его
    document.addEventListener('click', function(e) {
        if (!navMenu.contains(e.target) && !navToggle.contains(e.target)) {
            navMenu.classList.remove('active');
            navToggle.classList.remove('active');
        }
    });

    /**
     * Плавная прокрутка для якорных ссылок
     */
    navLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                const headerHeight = header.offsetHeight;
                const targetPosition = targetElement.offsetTop - headerHeight;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    /**
     * Анимация появления элементов при скролле
     */
    function animateOnScroll() {
        const elements = document.querySelectorAll('.feature-card, .tech-card, .screenshot-card, .about-item');
        
        elements.forEach(function(element) {
            const elementTop = element.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;
            
            if (elementTop < windowHeight - 100) {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }
        });
    }

    // Начальные стили для анимации
    const animatedElements = document.querySelectorAll('.feature-card, .tech-card, .screenshot-card, .about-item');
    animatedElements.forEach(function(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(30px)';
        element.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    });

    window.addEventListener('scroll', animateOnScroll);
    animateOnScroll(); // Проверка при загрузке

    /**
     * Активная ссылка при скролле
     */
    function setActiveLink() {
        const sections = document.querySelectorAll('section[id]');
        const scrollPosition = window.scrollY + header.offsetHeight + 100;

        sections.forEach(function(section) {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute('id');
            const activeLink = document.querySelector(`.nav-link[href="#${sectionId}"]`);

            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                navLinks.forEach(function(link) {
                    link.classList.remove('active');
                });
                if (activeLink) {
                    activeLink.classList.add('active');
                }
            }
        });
    }

    window.addEventListener('scroll', setActiveLink);

    /**
     * Обработка кнопок "Скачать демо"
     */
    const downloadButtons = document.querySelectorAll('.btn[href="#"]');
    downloadButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (this.getAttribute('href') === '#') {
                e.preventDefault();
                alert('Демо-версия будет доступна в ближайшее время!');
            }
        });
    });

    /**
     * Параллакс-эффект для Hero-секции
     */
    function parallaxEffect() {
        const heroCar = document.querySelector('.hero-car-icon');
        if (heroCar) {
            const scrolled = window.scrollY;
            heroCar.style.transform = `translateY(${scrolled * 0.3}px)`;
        }
    }

    window.addEventListener('scroll', parallaxEffect);
});