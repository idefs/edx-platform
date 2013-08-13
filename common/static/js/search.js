function correctionLink(event, spelling_correction){
    $("#searchbox")[0].value = spelling_correction;
    submitForms(false);
}

function submitForms(retain_page) {
    var get_data = [];
    var form_list = $(".auto-submit .parameter");
    for (var i in form_list){
        get_data.push.apply(get_data, form_list.eq(i).serializeArray());
    }
    var url = document.URL.split("?")[0]+"?";
    for (var o in get_data){
        if (retain_page === false){
            if (get_data[o].name == "page"){
                get_data[o].value = 1;
            }
        }
        url = url + (get_data[o].name + "=" +get_data[o].value + "&");
    }
    document.location.href = url.substring(0, url.length-1);
}

function incrementPage(){
    var current_page = $("#current-page input");
    current_page[0].value++;
    submitForms(true);
}

function decrementPage(){
    var current_page = $("#current-page input");
    current_page[0].value--;
    submitForms(true);
}

function clickHandle(e, retain_page){
    e.preventDefault();
    submitForms(retain_page);
}

function searchHandle(e, retain_page){
    if(e.keyCode === 13){
        e.preventDefault();
        submitForms(retain_page);
    }
}

function changeHandler(input, max_pages){
    if (input.value < 1) {input.value=1;}
    if (input.value > max_pages) {input.value=max_pages;}
}

function filterTrigger(input, type, retain_page){
    if (type == "org"){
        $("#selected-org").val($($(input).children(":first")).text());
    }

    if (type == "course"){
        $("#selected-course").val($(input).children(":first").text());
    }

    submitForms(retain_page);
}

function getParameters(){
    var paramstr = window.location.search.substr(1);
    var args = paramstr.split("&");
    var params = {};

    for (var i=0; i < args.length; i++){
        var temparray = args[i].split("=");
        params[temparray[0]] = temparray[1];
    }

    return params;
}

function getSearchAction(){
    var urlSplit = document.URL.split("/");
    var courseIndex = urlSplit.indexOf("courses");
    var searchAction = urlSplit.slice(courseIndex, courseIndex+4);
    searchAction.push("search")
    return searchAction.join("/");
}

function constructSearchBox(value){
    var searchWrapper = document.createElement("div");
    searchWrapper.className = "animated fadeInRight search-wrapper";
    searchWrapper.id = "search-wrapper";

    var searchForm = document.createElement("form");
    searchForm.className = "auto-submit";
    searchForm.id = "query-box";
    searchForm.action = "/"+getSearchAction();
    searchForm.method = "get";

    var searchBoxWrapper = document.createElement("div");
    searchBoxWrapper.className = "searchbox-wrapper";

    var searchBox = document.createElement("input");
    searchBox.id = "searchbox";
    searchBox.type = "text";
    searchBox.className = "searchbox parameter";
    searchBox.name = "s";
    searchBox.value = value;

    searchBoxWrapper.appendChild(searchBox);
    searchForm.appendChild(searchBoxWrapper);
    searchWrapper.appendChild(searchForm);

    return searchWrapper;
}

function replaceWithSearch(){
    $(this).addClass("animated fadeOut");
    var searchWrapper = constructSearchBox("");
    var width = $("div.search-icon").width();
    var height = $("div.search-icon").height();
    $(this).on('webkitAnimationEnd oanimationend oAnimationEnd msAnimationEnd animationend',
        function (e){
            $(this).parent().replaceWith(searchWrapper);
            $("#searchbox").css("width", width);
            $("#searchbox").css("height", height);
            // $('#search-bar').remove()
            if (document.URL.indexOf("search?s=") == -1){
                document.getElementById("searchbox").focus();
        }
    });
}

function updateOldSearch(){
    var params = getParameters();
    var newBox = constructSearchBox(old_query);
    var courseTab = $("a.search-bar").get(0);
    if (typeof courseTab != 'undefined'){
        courseTab.parentNode.replaceChild(newBox, courseTab);
    }
}

function paginate(element){
    var currentResults = parseInt($("._currentFilter span.count").text(), 10);
    var pages = Math.ceil(currentResults/10.0);
    var startPage = 1;
    if (document.location.href.match(/page=\d+/)){
        startPage = document.location.href.match(/page=(\d+)/)[1];
    }
    $(element).paginate({
        count       : pages,
        start       : startPage,
        display     : 5,
        border                  : true,
        border_color            : '#999',
        text_color              : '#999',
        background_color        : '#eee',
        border_hover_color      : '#ccc',
        text_hover_color        : '#999',
        background_hover_color  : '#fff',
        images                  : false,
        mouse                   : 'press',
        onChange                : function(page){
            var newPage = $(".jPag-current").text();
            if (document.location.href.match(/page=\d+/)){
                window.location.href = document.location.href.replace(/page=\d+/, "page=" + newPage);
            } else {
                window.location.href = document.location.href + "&page=" + newPage;
            }
        }
    });
    var lastButton = $("div.jPag-control-front");
    var selectorDiv = $("p.jPaginate div:not([class])");
    var currentLeft = parseInt(lastButton.css("left"),10);
    var adjustment = parseInt(selectorDiv.css("margin-left"), 10);
    var currentWidth = parseInt(selectorDiv.css("width"), 10);
    selectorDiv.css("width", currentWidth-adjustment);
    lastButton.css("left", currentLeft-adjustment);
    $("ul.jPag-pages").width($("ul.jPag-pages").width()+1);
}

function moveFilterClasses(){
    $("._currentFilter").removeClass("_currentFilter");
    if (document.location.href.match(/filter=\w+/)){
        var currentFilter = document.location.href.match(/filter=(\w+)/)[1];
        var newFilter = $("#"+currentFilter);
        newFilter.addClass("_currentFilter");
    }
    else {
        $("#all").addClass("_currentFilter");
    }
}

function changeFilter(){
    var newFilter = $(this).attr("id");
    var newUrl = "";
    if (document.location.href.match(/filter=\w+/)){
        newUrl = document.location.href.replace(/filter=\w+/, "filter=" + newFilter);
    } else {
        newUrl = document.location.href + "&filter=" + newFilter;
    }
    if (newUrl.match(/page=\d+/)){
        window.location.href = newUrl.replace(/page=\d+/, "page=1");
    } else {
        window.location.href = newUrl + "&page=1";
    }
}

$(document).ready(function(){
    moveFilterClasses();
    if (document.URL.indexOf("search?s=") !== -1){
        updateOldSearch();
    } else {
        $("a.search-bar").bind("click", replaceWithSearch);
    }

    if ($("p.pagination-stub").length > 0) {
        paginate($("p.pagination-stub").eq(0));
    }

    $("ul.menu li").bind("click", changeFilter);
});

