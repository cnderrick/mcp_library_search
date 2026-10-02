$(function() {
    $('.top_nav ul li.main').hover(function() {
        $(this).addClass('current');
        $(this).children('ul.sub_nav').stop(true, true).slideDown(100);
    },
    function() {
        $(this).removeClass('current');
        $(this).children('ul.sub_nav').stop(true, true).slideUp(100);
    });
});


