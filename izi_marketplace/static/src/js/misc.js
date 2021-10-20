odoo.define('izi_marketplace.framework', function (require) {
  "use strict";

  let core = require('web.core');
  let framework = require('web.framework');
  let originblockUI = framework.blockUI;
  let originUnblockUI = framework.unblockUI;

  function closeNotifications(params) {
    if (!params) {
      params = {}
    }
    let $notifs = $('.o_notification .o_close');
    if ($notifs.length > 0) {
      if (!params.force_show_number || params.close_on_finish) {
        setTimeout(function () {
          let $notif = [].shift.call($notifs);
          if ($notif) {
            $notif.click();
          }
          closeNotifications(params);
        }, 500);
      } else if ($notifs.length > params.force_show_number) {
        setTimeout(function () {
          let $notifs_to_close = $notifs.slice(0, $notifs.length - params.force_show_number);
          if ($notifs_to_close) {
            $notifs_to_close.click();
          }
          closeNotifications(params);
        }, 500);
      } else if ($notifs.length <= params.force_show_number) {
        setTimeout(function () {
          if (!params.hasOwnProperty('close_on_finish')) {
            params.close_on_finish = true;
          }
          closeNotifications(params);
        }, 500);
      } else {
        setTimeout(function () {
          closeNotifications(params);
        }, 500);
      }
    }
  }

  framework.blockUI = function () {
    closeNotifications({force_show_number: 1, close_on_finish: false});
    return originblockUI();
  }

  framework.unblockUI = function () {
    closeNotifications();
    return originUnblockUI();
  }

  function closeNotificationAction(parent, action) {
    let controller = parent.inner_widget.active_view.controller
    let params = action.params || {};
    closeNotifications(params);
    if (action.context.close_notifications_and_wizard) {
      parent.do_action({'type': 'ir.actions.act_window_close'});
    }
    controller.reload();
  }

  core.action_registry.add('close_notifications', closeNotificationAction);
});