// Fetch data about badges via JSONP, so that the progress page does
// not fail to load if the badge service is failing.

$(document).ready(function() {

  badges_element = $("#badges");

  badges_element.css("position", "relative");
  badges_element.css("text-align", "center");

  var get_badges = function() {
    var url = badge_service_url + "badges/?format=jsonp&email=" + email + "&badgeclass__issuer__course=" + course_id + "&callback=?";
    return $.getJSON(url, function(data){});
  };

  var get_badgeclasses = function() {
    var url = badge_service_url + "badgeclasses/?format=jsonp&issuer__course=" + course_id + "&callback=?";
    return $.getJSON(url, function(data){});
  };

  var set_html_to_badges = function(element) {
    $.when(get_badges(), get_badgeclasses()).done(function(badges_data, badgeclasses_data) {
      var badges_list = badges_data[0].results;
      var badgeclasses_list = badgeclasses_data[0].results;

      if (badgeclasses_list.length !== 0) {
        var badges_html = "<div style=\"overflow-x:scroll; overflow-y:hidden; white-space:nowrap;\">";

        for (var i=0; i<badgeclasses_list.length; i++) {
          var badgeclass = badgeclasses_list[i];

          badges_html += "<a href=\"./badges\"><img src=\""+badgeclass.image+"\" ";

          if (is_earned(badgeclass, badges_list)) {
            badges_html += "class=\"badgelet\" title=\""+badgeclass.name+"\"";
          } else {
            badges_html += "class=\"badgelet unlockable\"";
          }

          badges_html += " /></a>";

        }
        badges_html += "</div>";

        element.html(badges_html);
      }
    });
  };

  //Determine whether a badgeclass has been earned -- whether it is in badges_list.
  var is_earned = function(badgeclass, badges_list) {
    for (var i=0; i<badges_list.length; i++) {
      if (badges_list[i].badge.indexOf(badgeclass.href) != -1) {
        return true;
      }
    }
    return false;
  };

  set_html_to_badges(badges_element);

});
