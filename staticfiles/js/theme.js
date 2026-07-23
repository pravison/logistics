;
(function($) {
    "use strict";

    //* Navbar Fixed  
    function navbarFixed() {
        if ($('.main_header_area').length) {
            $(window).on('scroll', function() {
                var scroll = $(window).scrollTop();
                if (scroll >= 295) {
                    $(".main_header_area").addClass("navbar_fixed");
                } else {
                    $(".main_header_area").removeClass("navbar_fixed");
                }
            });
        };
    };


    //* Parallaxmouse js
    function parallaxMouse() {
        if ($('#parallax').length) {
            var scene = document.getElementById('parallax');
            var parallax = new Parallax(scene);
        };
    };

    //* Counter Js 
    function counterUp() {
        if ($('.countarup_area, .agency_contant').length) {
            $('.counter').counterUp({
                delay: 10,
                time: 400
            });
        };
    };

    //* Client Logo Js 
    function owl_Carousel() {
        if ($('.client_logo, .testimonial_carousel').length) {
            $('.client_logo').owlCarousel({
                loop: true,
                margin: 0,
                nav: false,
                items: 4,
                responsive: {
                    0: {
                        items: 1,
                        margin: 0,
                    },
                    400: {
                        items: 2,
                    },
                    767: {
                        items: 4,
                    },
                }
            });

            //testimonial_carousel
            var carousel = $(".testimonial_carousel");
            $('.testimonial_carousel').owlCarousel({
                loop: true,
                margin: 30,
                nav: true,
                items: 1.5,
                navText: ["<i class='flaticon-left-arrow'></i>", "<i class='flaticon-next'></i>"],
                responsive: {
                    0: {
                        items: 1,
                        margin: 0,
                    },
                    767: {
                        items: 1.5,
                    },
                }
            });

            checkClasses();
            carousel.on('translated.owl.carousel', function(event) {
                checkClasses();
            });

            function checkClasses() {
                var total = $('.testimonial_carousel .owl-stage .owl-item.active').length;
                $('.testimonial_carousel .owl-stage .owl-item').removeClass('firstActiveItem');
                $('.testimonial_carousel .owl-stage .owl-item.active').each(function(index) {
                    if (index === 0) {
                        // this is the first one
                        $(this).addClass('firstActiveItem');
                    }
                });
            };

            //testimonial_carousel 
            $('.testimonial_2').owlCarousel({
                loop: true,
                margin: 0,
                nav: true,
                items: 1,
                navText: ["<i class='flaticon-left-arrow'></i>", "<i class='flaticon-next'></i>"],
            });
        };
    };


    //* Magnificpopup js
    function magnificPopup() {
        if ($('.popup-youtube').length) {
            //Video Popup
            $('.popup-youtube').magnificPopup({
                disableOn: 700,
                type: 'iframe',
                mainClass: 'mfp-fade',
                removalDelay: 160,
                preloader: false,
                fixedContentPos: false,
            });
        };
    };

    //* Select js
    function selectmenu() {
        if ($('.post_select').length) {
            $('select').niceSelect();
        };
    };

    //* Isotope js
    function protfolioIsotope() {
        if ($('.portfolio').length) {
            // Activate isotope in container
            $(".portfolio_inner").imagesLoaded(function() {
                $(".portfolio_inner").isotope({
                    layoutMode: 'fitRows',
                });
            });

            // Add isotope click function 
            $(".portfolio_filter li").on('click', function() {
                $(".portfolio_filter li").removeClass("active");
                $(this).addClass("active");
                var selector = $(this).attr("data-filter");
                $(".portfolio_inner").isotope({
                    filter: selector,
                    animationOptions: {
                        duration: 450,
                        easing: "linear",
                        queue: false,
                    }
                });
                return false;
            });
        };
    };

    //* Rang slider js
    function sliderRange() {
        if ($('#slider-range').length) {
            $("#slider-range").slider({
                range: true,
                min: 0,
                max: 200,
                values: [0, 150],
                slide: function(event, ui) {
                    $("#amount").val("$" + ui.values[0] + " - $" + ui.values[1]);
                }
            });
            $("#amount").val("$" + $("#slider-range").slider("values", 0) +
                " - $" + $("#slider-range").slider("values", 1));
        };
    };

    // Product value
    function productValue() {
        var inputVal = $("#product-value");
        if (inputVal.length) {
            $('#value-decrease').on('click', function() {
                inputVal.html(function(i, val) {
                    return val * 1 - 1
                });
            });
            $('#value-increase').on('click', function() {
                inputVal.html(function(i, val) {
                    return val * 1 + 1
                });
            });
        }
    }
    // CountDown Js 
    function countDown() {
        if ($('.countdown').length) {
            $('.countdown').dsCountDown({
                endDate: new Date("November 01, 2019 20 23:59:00"),
            });
        }
    }

    // Scroll to top
    function scrollToTop() {
        if ($('.scroll-top').length) {
            $(window).on('scroll', function() {
                if ($(this).scrollTop() > 200) {
                    $('.scroll-top').fadeIn();
                } else {
                    $('.scroll-top').fadeOut();
                }
            });
            //Click event to scroll to top
            $('.scroll-top').on('click', function() {
                $('html, body').animate({
                    scrollTop: 0
                }, 1000);
                return false;
            });
        }
    }


    // Preloader JS
    function preloader() {
        if ($('.preloader').length) {
            $(window).on('load', function() {
                $('.preloader').fadeOut();
                $('.preloader').delay(50).fadeOut('slow');
            })
        }
    }


    /*Function Calls*/
    new WOW().init();
    navbarFixed();
    parallaxMouse();
    counterUp();
    owl_Carousel();
    selectmenu();
    protfolioIsotope();
    sliderRange();
    productValue();
    countDown();
    scrollToTop();
    preloader();

})(jQuery);