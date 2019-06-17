(window.webpackJsonp=window.webpackJsonp||[]).push([[14],{"splunkjs/mvc/debugger":function(module,exports,__webpack_require__){var __WEBPACK_AMD_DEFINE_RESULT__;void 0===(__WEBPACK_AMD_DEFINE_RESULT__=function(require,exports,module){var _=__webpack_require__("require/underscore"),Backbone=__webpack_require__("require/backbone"),BaseManager=__webpack_require__("splunkjs/mvc/basemanager"),BaseSplunkView=__webpack_require__("splunkjs/mvc/basesplunkview"),BaseTokenModel=__webpack_require__("splunkjs/mvc/basetokenmodel"),SearchModels=__webpack_require__("splunkjs/mvc/searchmodel"),console=window.console,indent=function(count){for(var str="",i=0;i<count;i++)str+="    ";return str},warn=function(msg){return"WARNING: "+msg},categoryEnum={MANAGER:"manager",VIEW:"view",NAMESPACE:"namespace",UNKNOWN:"unknown"};return Backbone.Model.extend({ready:!1,initialize:function(){this.registry=this.get("registry"),this.registry?console.log("The Splunkjs debugger is running. For help, enter 'splunkjs.mvc.Debugger.help()'"):console.log("splunk.mvc debugging interface could not find the registry")},isReady:function(){return this.ready},getDebugData:function(){var that=this,components=[],registeredComponentKeys=that.registry.getInstanceNames();_.each(registeredComponentKeys,function(elementID){var registryElement=that.registry.getInstance(elementID),type=that._getComponentType(registryElement),category=that._getComponentCategory(registryElement),validOptions=[],elementMetaData={id:elementID,category:category,type:type,warnings:[]};if(category===categoryEnum.VIEW){var managerid=null,settings={};validOptions=that._getValidViewOptions(registryElement),registryElement.settings&&(managerid=registryElement.settings.get("managerid")||null,settings=_.clone(registryElement.settings.attributes),_.each(_.keys(settings),function(key){if(!_.contains(validOptions,key)){var partOne=key.split(".")[0];"mapping"!==partOne&&"charting"!==partOne&&elementMetaData.warnings.push(warn(key+" is not a recognized setting."))}})),elementMetaData.managerid=managerid,elementMetaData.settings=settings,elementMetaData.el=registryElement.el||"no element set"}if(category===categoryEnum.NAMESPACE&&(elementMetaData.tokens=[],_.each(registryElement.attributes,function(value,key){var tokenData={name:key,value:value,listenerIds:[]};elementMetaData.tokens.push(tokenData)})),category===categoryEnum.MANAGER){if(validOptions=that._getValidManagerOptions(registryElement),registryElement.attributes){var attributes=_.clone(registryElement.attributes);_.each(_.keys(attributes),function(key){_.contains(validOptions,key)||elementMetaData.warnings.push(warn(key+" is not a recognized attribute"))})}elementMetaData.attributes=registryElement.attributes,elementMetaData.query=registryElement.query,elementMetaData.search=registryElement.search}category!==categoryEnum.NAMESPACE&&(elementMetaData.bindings=that._getComponentBindings(elementID)),components.push(elementMetaData)});var managers=_.where(components,{category:categoryEnum.MANAGER}),views=_.where(components,{category:categoryEnum.VIEW}),namespaces=_.where(components,{category:categoryEnum.NAMESPACE});return _.each(managers,function(manager){manager.viewIds=_.pluck(_.where(views,{managerid:manager.id}),"id"),manager.viewIds.length<1&&manager.warnings.push(warn("no views bound to search manager."))}),_.each(views,function(view){view.managerid&&(_.contains(_.pluck(managers,"id"),view.managerid)||view.warnings.push(warn(view.managerid+" is not a registered manager.")))}),_.each(namespaces,function(namespace){_.each(namespace.tokens,function(token){var listeners=_.filter(_.union(managers,views),function(item){return _.some(item.bindings,function(binding){if(binding&&binding.observes&&binding.observes.length>0)return _.some(binding.observes,function(observes){return observes.namespace===namespace.id&&observes.name===token.name})})});token.listenerIds=_.pluck(listeners,"id")})}),components},_getValidViewOptions:function(element){var options=["id","name","managerid","manager","app","el","data"];return element.constructor.prototype.options&&(options=_.union(options,_.keys(element.constructor.prototype.options))),options},_getValidManagerOptions:function(element){return _.union(["app","id","owner","name","data"],_.keys(element.constructor.prototype.defaults)||[],SearchModels.SearchSettingsModel.ALLOWED_ATTRIBUTES)},_getComponentType:function(component){var type="Unknown type";if(component.moduleId){var name=component.moduleId.split("/").pop();name.length>0&&(type=name)}return type},_getComponentCategory:function(component){var category=categoryEnum.UNKNOWN;return component instanceof BaseSplunkView?category=categoryEnum.VIEW:component instanceof BaseManager?category=categoryEnum.MANAGER:component instanceof BaseTokenModel&&(category=categoryEnum.NAMESPACE),category},_getComponentTokenBoundProperties:function(componentId){var bindings=this._getComponentBindings(componentId);return _.keys(bindings)},_getComponentBindings:function(componentId){var component=this.registry.getInstance(componentId),bindings={};return component&&component.settings&&(bindings=_.extend(bindings,_.clone(component.settings._bindings))),bindings},createError:function(message){return message},printViewInfo:function(){var views=this.getInfoForViews();console.log("Views:"),_.each(views,function(view){console.log(indent(1)+"ID: "+view.id),console.log(indent(2)+"Type: "+view.type),console.log(indent(2)+"Manager: "+view.managerid),console.log(indent(2)+"Element: ",view.el),console.log(indent(2)+"Settings: "),_.each(_.keys(view.settings),function(key){var tokenInfo="",binding=view.bindings[key];binding&&binding.observes&&binding.observes.length>0&&(tokenInfo=" [bound: "+JSON.stringify(binding.template)+", resolved: "+JSON.stringify(binding.computeValue(!0))+"]");console.log(indent(3)+key+": "+JSON.stringify(view.settings[key])+tokenInfo)}),view.warnings.length>0&&(console.log(indent(2)+"WARNINGS: "),_.each(view.warnings,function(warning){console.log(indent(3)+warning)}))})},printSearchManagerInfo:function(){var managers=this.getInfoForManagers();console.log("Search Managers:"),_.each(managers,function(manager){if(console.log(indent(1)+"ID: "+manager.id),console.log(indent(2)+"Type: "+manager.type),manager.attributes){console.log(indent(2)+"Attributes: ");var propertiesToSkip=SearchModels.SearchSettingsModel.ALLOWED_ATTRIBUTES;_.each(manager.attributes,function(value,key){_.contains(propertiesToSkip,key)||console.log(indent(3)+key+": "+JSON.stringify(value))})}manager.settings&&manager.settings.attributes&&(console.log(indent(2)+"Search Properties: "),_.each(manager.settings.attributes,function(value,key){var tokenInfo="",binding=manager.bindings[key];binding&&binding.observes&&binding.observes.length>0&&(tokenInfo=" [bound: "+JSON.stringify(binding.template)+", resolved: "+JSON.stringify(binding.computeValue(!0))+"]");console.log(indent(3)+key+": "+JSON.stringify(value)+tokenInfo)})),console.log(indent(2)+"Views bound to manager: "),_.each(manager.viewIds,function(id){console.log(indent(3)+id)}),manager.warnings.length>0&&(console.log(indent(2)+"WARNINGS: "),_.each(manager.warnings,function(warning){console.log(indent(3)+warning)}))})},printTokenNamespaceInfo:function(){var namespaces=this.getInfoForNamespaces();console.log("Token Namespaces:"),_.each(namespaces,function(namespace){console.log(indent(1)+"ID: "+namespace.id),console.log(indent(2)+"Type: "+namespace.type),console.log(indent(2)+"Tokens: "),_.each(namespace.tokens,function(token){console.log(indent(3)+token.name+": "),console.log(indent(4)+"value: "+JSON.stringify(token.value)),console.log(indent(4)+"listeners: "+token.listenerIds.join(", "))})})},printComponentInfo:function(){this.printViewInfo(),this.printSearchManagerInfo(),this.printTokenNamespaceInfo()},printWarnings:function(){var components=this.getDebugData();console.log("WARNINGS:"),_.each(components,function(item){item.warnings.length>0&&(console.log(indent(1),"ID: "+item.id+": "),_.each(item.warnings,function(warning){console.log(indent(2)+warning)}))})},_getInfoForComponents:function(ctype){var components=this.getDebugData();return void 0!==ctype?_.where(components,{category:categoryEnum[ctype]}):components},getInfoForViews:function(){return this._getInfoForComponents("VIEW")},getInfoForManagers:function(){return this._getInfoForComponents("MANAGER")},getInfoForNamespaces:function(){return this._getInfoForComponents("NAMESPACE")},help:function(){console.log("Splunkjs Debugger Commands"),console.log(indent(1)+"- printWarnings(): Prints all warnings to the console."),console.log(indent(1)+"- printComponentInfo(): Prints all debug info and warnings to the console by component."),console.log(indent(1)+"- printViewInfo(): Prints debug info for all Splunk views."),console.log(indent(1)+"- printSearchManagerInfo(): Prints debug info for all Splunk search managers."),console.log(indent(1)+"- printTokenNamespaceInfo(): Prints debug info for Splunk token namespaces."),console.log(indent(1)+"- getDebugData(): Returns all debug metadata for components and namespaces."),console.log(indent(1)+"- getInfoForViews(): Returns debug metadata for all Splunk views."),console.log(indent(1)+"- getInfoForManagers(): Returns debug metadata for all Splunk managers."),console.log(indent(1)+"- getInfoForNamespaces(): Returns debug metadata for all Splunk token namespaces.")}})}.call(exports,__webpack_require__,exports,module))||(module.exports=__WEBPACK_AMD_DEFINE_RESULT__)}}]);