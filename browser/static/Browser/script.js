var current_image = 0;
var max_slide = 15;
var images = [];
$(".fa-file-image").each(function() {
    images.push(encodeURI('?open=' + current + $(this).parent().next().text()));
});

$(".folder").click(function() {
    console.log(this.children[1].innerText);
    if (this.children[1].innerText == "..") {
        t = current.slice(0, -1).split("/");
        t.pop();
        if (t.length == 0) {
            window.location.search = "";
        } else {
            window.location.search = "?path=" + t.join("/") + "/";
        }
    } else {
        window.location.search = "?path=" + current + this.children[1].innerText;
    }
});
$(".files").click(function() {
    console.log("?open=" + current + this.children[1].innerText);
});

function change_href(e) {
    if ($(e.target).prop("tagName") == 'SPAN') {
        var v = $(e.target).parent().children();
        var t = "";
        for (i = 0; i < v.length; i++) {
            t += v[i].innerText;
            if (v[i] == e.target)
                break;
        }
        window.location.search = "?path=" + t;
    } else if ($(e.target).prop("tagName") == 'I') {
        window.location.search = "";
    }
}

function show_alert(txt) {
    var div = document.createElement("div");
    div.innerText = txt;
    div.classList.add("alert", "alert-dark");
    div.setAttribute('role', 'alert');

    var btn = document.createElement("button");
    btn.classList.add("close");
    btn.setAttribute('type', 'button');
    btn.setAttribute('data-dismiss', 'alert');
    btn.innerHTML = '&times;';
    div.appendChild(btn);

    $("#alert_box").prepend(div);
    console.log(txt);
    setTimeout(function() {
        div.style.display = "none";
    }, 5000);
}

function show_error(txt) {
    var div = document.createElement("div");
    div.innerText = txt;
    div.classList.add("alert", "error-dark");
    div.setAttribute('role', 'alert');

    var btn = document.createElement("button");
    btn.classList.add("close");
    btn.setAttribute('type', 'button');
    btn.setAttribute('data-dismiss', 'alert');
    btn.innerHTML = '&times;';
    div.appendChild(btn);

    $("#alert_box").prepend(div);
    console.log(txt);
}

const copyToClipboard = str => {
    const el = document.createElement('textarea');
    el.value = str;
    el.setAttribute('readonly', '');
    el.style.position = 'absolute';
    el.style.left = '-9999px';
    document.body.appendChild(el);
    const selected = document.getSelection().rangeCount > 0 ? document.getSelection().getRangeAt(0) : false;
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    if (selected) {
        document.getSelection().removeAllRanges();
        document.getSelection().addRange(selected);
    }
};

function downloadURI(file_name) {
    var link = document.createElement("a");
    link.style.display = "none";
    link.setAttribute('download', file_name);
    link.setAttribute('type', type);
    link.href = "?open=" + current + file_name;
    document.body.appendChild(link);
    console.log(link);
    link.click();
    link.remove();
}

function file_handler(file_name, method) {
    $.post(url, {
        method: method,
        file: file_name
    }, function(data, status) {
        if (status == "success") {
            console.log(data);
        } else {
            console.log(data);
            console.log(status);
            alert("Data: " + data + "\nStatus: " + status);
        }
    }, "json");
}

function delete_file(file_name, el) {
    $("#file-delete-path").text(file_name);
    $("#deletefileforreal").unbind();
    $("#deletefileforreal").click(function() {
        $("#deletePopUp").modal("hide");
        $.post(url, {
            method: "delete",
            file: file_name
        }, function(data, status) {
            if (status == "success") {
                if ('alert' in data) {
                    show_alert(data['alert']);
                }
                if ('error' in data) {
                    show_error(data['error']);
                }
                el.remove();
            } else {
                console.log(data);
                alert("Data: " + data + "\nStatus: " + status);
            }
        }, "json");
    });
    $("#deletePopUp").modal("show");
}

var mySwiper = new Swiper('.swiper-container', {
    slidesPerView: 1,
    zoom: {
        maxRatio: 5,
    },
    centeredSlides: true,
    spaceBetween: 10,
    direction: 'horizontal',
    loop: false,
    effect: 'coverflow',
    grabCursor: true,
    coverflowEffect: {
        rotate: 50,
        stretch: 0,
        depth: 100,
        modifier: 1,
        slideShadows: true,
    },
    navigation: {
        nextEl: '.swiper-button-next',
        prevEl: '.swiper-button-prev',
    },
    keyboard: {
        enabled: true,
        onlyInViewport: true,
    },
    breakpoints: {
        '@0.00': {
            slidesPerView: 1.2,
            spaceBetween: 10,
            direction: 'vertical',
        },
        '@0.75': {
            slidesPerView: 1.1,
            spaceBetween: 5,
            direction: 'vertical',
        },
        '@1.00': {
            slidesPerView: 1,
            spaceBetween: 10,
            direction: 'horizontal',
        },
        '@1.50': {
            slidesPerView: 2,
            spaceBetween: 20,
            direction: 'horizontal',
        },
    }
});

function swiper_slide(url) {
    var img = document.createElement("img");
    img.classList.add("img-fluid");
    img.setAttribute("src", url);
    img.setAttribute("style", "max-height:100%;");

    var zoom_div = document.createElement("DIV")
    zoom_div.classList.add("swiper-zoom-container");
    zoom_div.appendChild(img);

    var div = document.createElement("DIV");
    div.classList.add("swiper-slide");
    div.appendChild(zoom_div);
    return div;
}

function append_slide() {
    current_image = images.indexOf($(".swiper-slide").last().children()[0].children[0].getAttribute("src"));
    if (current_image == -1) {
        current_image = images.indexOf(encodeURI($(".swiper-slide").last().children()[0].children[0].getAttribute("src")));
    }
    if (images[current_image + 1] != undefined) {
        console.log("Appending ", images[current_image + 1]);
        mySwiper.appendSlide(swiper_slide(images[current_image + 1]));
        while (mySwiper.slides.length > max_slide) {
            mySwiper.removeSlide(0);
        }
        mySwiper.update();
    }
}

function prepend_slide() {
    current_image = images.indexOf($(".swiper-slide").first().children()[0].children[0].getAttribute("src"));
    if (current_image == -1) {
        current_image = images.indexOf(encodeURI($(".swiper-slide").first().children()[0].children[0].getAttribute("src")));
    }
    if (images[current_image - 1] != undefined) {
        console.log("Prepending ", images[current_image - 1]);
        mySwiper.prependSlide(swiper_slide(images[current_image - 1]));
        mySwiper.update();
    }
}

function view_initialize(file_name) {
    current_image = images.indexOf(encodeURI("?open=" + current + file_name));
    $("#view_box").show();
    mySwiper.appendSlide(swiper_slide("?open=" + current + file_name));
    mySwiper.update();
    append_slide();
    prepend_slide();
    append_slide();
    prepend_slide();
    $("#view_box_name").text(file_name);
}

mySwiper.on('slideChange', function() {
    var file_name = mySwiper.slides[mySwiper.realIndex].children[0].children[0].getAttribute("src");
    $("#view_box_name").text(file_name.split("/").pop());
    if (mySwiper.realIndex <= 2) {
        setTimeout(prepend_slide, 300);
    }
    if (mySwiper.realIndex >= mySwiper.slides.length - 3) {
        setTimeout(append_slide, 300);
    }
});

$(function() {
    $.contextMenu({
        selector: '.files',
        build: function($triggerElement, e) {
            file_name = $triggerElement.children()[1].innerText;
            type = $triggerElement.attr("type");
            return {
                callback: function(key, options) {
                    console.log("clicked: " + key + " on " + file_name);
                    if (key == "download") {
                        downloadURI(file_name);
                    } else if (key == "copy_path") {
                        copyToClipboard(current + file_name);
                    } else if (key == "delete") {
                        delete_file(current + file_name, $triggerElement);
                    } else if (key == "view") {
                        if (type.split("/")[0] == "image")
                            view_initialize(file_name);
                        else if (type.split("/")[0] == "video") {
                            player.source = {
                                type: 'video',
                                title: file_name,
                                sources: [{
                                    src: encodeURI("?open=" + current + file_name),
                                }, ],
                            };
                            player.play();
                            $("#video_box").show();
                        }
                    } else if (key == "rename") {
                        $('#new_file_name').val(file_name);
                        $('#new_file_name').attr('data-old-name', file_name);
                        $('#file_rename_box').css("display", "flex");
                    }

                },
                items: {
                    "view": {
                        name: "View Item",
                        icon: "fas fa-eye",
                        disabled: function(key, opt) {
                            return (type.split("/")[0] != 'image' && type.split("/")[0] != 'video')
                        }
                    },
                    "download": {
                        name: "Download",
                        icon: "fas fa-download",
                        disabled: function(key, opt) {
                            return (type === 'PermissionError')
                        }
                    },
                    "sep1": {
                        "type": "cm_separator"
                    },
                    "rename": {
                        name: "Rename",
                        icon: "fas fa-edit",
                    },
                    "copy_path": {
                        name: "Copy Path",
                        icon: "far fa-clipboard"
                    },
                    "cut": {
                        name: "Cut",
                        icon: "cut",
                        disabled: true
                    },
                    "paste": {
                        name: "Paste",
                        icon: "paste",
                        disabled: true
                    },
                    "sep2": {
                        "type": "cm_separator"
                    },
                    "delete": {
                        name: "Delete",
                        icon: "delete"
                    },
                }
            };
        }
    });
});

/*tippy('.files', {
  placement: 'right-start',
  delay: [1000, 0],
  arrow: false,
  followCursor: 'initial',
  theme: 'blackwhite',
  interactiveDebounce: 0,
});

const rightClickableArea = document.querySelector('#tempId');
const instance = tippy(rightClickableArea, {
  allowHTML: true,
  placement: 'right-start',
  trigger: 'manual',
  interactive: true,
  arrow: false,
  offset: [0, 0],
  theme: 'blackwhite',
});
rightClickableArea.addEventListener('contextmenu', (event) => {
  if (event.target.tagName == "TD"){
    event.preventDefault();
    console.log(event.target.parentNode);
    var c = event.target.innerText
    instance.setProps({
      content: "<a class=\"contex-item\" href=\"#\">View1</a><a class=\"contex-item\" href=\"#\">View</a><a class=\"contex-item\" href=\"#\">ViewViewViewViewView</a>",
      getReferenceClientRect: () => ({
        width: 0,
        height: 0,
        top: event.clientY,
        bottom: event.clientY,
        left: event.clientX,
        right: event.clientX,
      }),
    });
    instance.show();
  }
});*/
