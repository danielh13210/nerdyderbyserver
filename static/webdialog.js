function getTextWidth_(text, font) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    context.font = font; // Set the font style
    const metrics = context.measureText(text);
    return metrics.width; // Return the width of the text
}

let dialog_showing_=false;
let active_dialog_=null;
let upcoming_dialogs_=[];
function showDialog_(html,title,buttons,onClose,submitButton,hasSVGFiles){
    // Queue upcoming dialogs if one is already showing
    if(dialog_showing_){
        upcoming_dialogs_.push({"html":html, "title":title, "button":buttons});
        return;
    }
    //create the dialog box
    const dialog = document.createElement('div');
    dialog.classList.add('dialog');
    dialog.style.display="none";
    setTimeout(()=>{dialog.style.display="";},500);

    //place the text in the box
    dialog.innerHTML=html?html:"";

    //create the cover board to prevent clicking outside the dialog box while it is open
    const coverBoard = document.createElement('div');
    coverBoard.classList.add('dialog-modal-coverboard');

    //create the close button
    const closeButton = document.createElement('button');
    closeButton.classList.add("dialog-close");
    const x = document.createElement('p');
    x.classList.add("dialog-xbutton");
    x.innerHTML="x";
    closeButton.appendChild(x);
    let overflow_prev=document.body.style.overflow;
    function close_dialog(callOnClose=false){ 
        document.body.removeChild(dialog);
        document.body.removeChild(coverBoard);
        document.body.style.overflow=overflow_prev;
        dialog_showing_=false;
        if(callOnClose)
            onClose();
        // If there are more dialogs queued, show the next one
        if(upcoming_dialogs_.length>0){
            let next_dialog=upcoming_dialogs_.shift();
            showDialog_(next_dialog["html"],next_dialog["title"],next_dialog["buttons"]);
        }
    }
    closeButton.addEventListener('click',()=>{close_dialog(true);});

    //create the dialog title
    const dialogTitle=document.createElement("h3");
    title=(typeof title == "string")?title:"[In-page dialog]"
    dialogTitle.innerText=title;
    dialogTitle.classList.add("dialog-title");

    // set dialog width
    dialog.style.minWidth=`${getTextWidth_(title,"500 1.75rem Arial")+222}px`;

    //create the button box
    let buttonBoxContainer=document.createElement("div");
    buttonBoxContainer.classList.add("dialog-buttonbox-container");
    let buttonBox=document.createElement("div");
    buttonBox.classList.add("dialog-buttonbox");
    if(typeof buttons!="object"){
        buttons=[{"text":"OK","action":"close_dialog"}];
    }
    buttons.forEach(button_descriptor => {
        let button=document.createElement("button");
        button.classList.add("dialog-button");
        button.innerHTML=button_descriptor.text;
        let action=button_descriptor.action;
        if (typeof action!="function"){
            action=()=>true;
        }
        button.addEventListener("click",(e)=>{
            close_dialog();
            action(e);
        });
        buttonBox.appendChild(button);
    });

    //add the elements
    buttonBoxContainer.appendChild(buttonBox);
    dialog.appendChild(buttonBoxContainer);
    dialog.appendChild(closeButton);
    dialog.appendChild(dialogTitle);
    document.body.appendChild(coverBoard);
    document.body.appendChild(dialog);
    document.body.style.overflow="hidden";
    if(hasSVGFiles)
        SVGImporter.reimport();
    dialog_showing_=true;
    active_dialog_ = {
        submitButton: submitButton,
        close: close_dialog
    };
    return active_dialog_;
}


export default {
    showDialog: function showDialog(html,title,buttons){
        //ensure security
        let cleanHTML=DOMPurify.sanitize(html,{
            ALLOWED_TAGS:['h1', 'h2', 'h3', 'h4', 'h5', 'h6','p','b','i','em','strong','br','img'],
            ALLOWED_ATTR:['src','id','class','style']
        });
        let tempDiv=document.createElement("div");
        tempDiv.innerHTML=cleanHTML;
        Array.from(tempDiv.querySelectorAll('*')).forEach((elem)=>{
            if(elem.tagName.toLowerCase()!=="img"){
                elem.removeAttribute('src');
            }
        });
        cleanHTML=tempDiv.innerHTML;
        showDialog_(cleanHTML,title,buttons);
    }
}

document.addEventListener("DOMContentLoaded",()=>{
    document.head.innerHTML+=`
    <link href="/static/dialog.css" rel="stylesheet" />
    `
});
