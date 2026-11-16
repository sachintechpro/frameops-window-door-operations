/* FrameOps mobile table presentation.
 * Enriches cells with their existing column titles for readable mobile cards.
 * No navigation, data, API, permissions, submit or form logic is changed.
 */
(function(){
  "use strict";
  let pending=false;
  function decorate(){
    pending=false;
    const root=document.getElementById("app");
    if(!root)return;
    for(const table of root.querySelectorAll(".ops-table,.data-table")){
      const headings=[...table.querySelectorAll("thead th")]
        .map((th,i)=>th.textContent.trim()||(i===6?"Open":"Action"));
      for(const row of table.querySelectorAll("tbody tr")){
        const cells=[...row.children].filter(el=>el.tagName==="TD");
        let offset=0;
        for(const cell of cells){
          if(cell.hasAttribute("colspan")){offset+=Math.max(1,Number(cell.getAttribute("colspan"))||1);continue;}
          const label=headings[offset]||"Detail";
          if(cell.dataset.cellLabel!==label)cell.dataset.cellLabel=label;
          offset++;
        }
      }
    }
  }
  function queue(){
    if(pending)return;
    pending=true;
    queueMicrotask(decorate);
  }
  function init(){
    const root=document.getElementById("app");
    if(!root)return;
    decorate();
    new MutationObserver(queue).observe(root,{subtree:true,childList:true});
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
  else init();
})();
