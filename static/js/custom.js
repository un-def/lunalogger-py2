function magnetify(message) {
  return message.replace(/(magnet:\?xt=urn:tree:tiger:[A-Za-z0-9]{39}&amp;xl=(\d+)&amp;dn=([^\s]+))/gm, makeMagnetLink)
}

function makeMagnetLink(_, magnet, xl, dn) {
  var i = Math.floor(Math.log(xl) / Math.log(1024));
  var filesize = (xl / Math.pow(1024, i)).toFixed(2) * 1 + " " + ["байт", "кБ", "МБ", "ГБ", "ТБ"][i];
  return "<a href=\"" + magnet + "\">" + decodeURIComponent(dn.replace(/\+/g, "%20")) + " (" + filesize + ")</a>"
}

function makeLinks() {
  $(".linkify").each(function () {
    $(this).html(magnetify($(this).html()));
  });
  $(".linkify").linkify();
}

function showMsgLink(event) {
  if (event.pageX < this.offsetLeft) {
    var link = $(location).attr('protocol') + "//" + $(location).attr('host') + $(location).attr('pathname') + "#;" + $(this).attr("id");
    $("#log-modal-link").attr("href", link);
    $("#log-modal-link").text(decodeURIComponent(link));
    $("#log-modal").modal("show");
  }
}
