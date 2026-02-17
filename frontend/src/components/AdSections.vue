<script setup>
import FieldsTable from './FieldsTable.vue'
import { escapeHtml } from '../utils/format'

const props = defineProps({
  account: { type: Object, required: true },
  renderGroupsHtml: { type: Function, default: null },
  renderManagerHtml: { type: Function, default: null },
})
const emit = defineEmits(['open-dn'])

function dnLinksHtml(dnString) {
  if (!dnString) return ''
  return dnString.split(';').map(s => s.trim()).filter(Boolean).map(dn => {
    const cn = dn.match(/^CN=([^,]+)/i)
    const display = cn ? cn[1] : dn
    return `<a class="ucard-link dn-link" href="#" data-dn="${escapeHtml(dn)}">${escapeHtml(display)}</a>`
  }).join('; ')
}

function groupsHtml(groupsStr) {
  if (props.renderGroupsHtml) return props.renderGroupsHtml(groupsStr)
  if (!groupsStr) return ''
  return groupsStr.split(';').map(g => g.trim()).filter(Boolean).map(g => escapeHtml(g)).join('; ')
}

function managerHtml(a) {
  if (props.renderManagerHtml) return props.renderManagerHtml(a)
  return dnLinksHtml(a.manager)
}

function onClick(e) {
  const link = e.target.closest('[data-dn]')
  if (!link) return
  e.preventDefault()
  emit('open-dn', link.dataset.dn, link.textContent.trim())
}
</script>

<template>
  <div @click="onClick">
    <div class="ucard-ad-section-label">Основные</div>
    <FieldsTable :pairs="[
      ['ФИО', account.display_name], ['Имя', account.given_name], ['Фамилия', account.surname_ad],
      ['UPN', account.upn], ['Email', account.email],
      ['Телефон', account.phone], ['Мобильный', account.mobile],
      ['Описание', account.description],
    ]" />
    <div class="ucard-ad-section-label">Должность</div>
    <FieldsTable :pairs="[
      ['Должность', account.title], ['Отдел', account.department], ['Компания', account.company],
      ['Тип сотрудника', account.employee_type], ['Расположение', account.location],
      ['Адрес', account.street_address],
      ['Руководитель', { html: managerHtml(account) }],
      ['Таб. номер', account.employee_number],
    ]" />
    <div class="ucard-ad-section-label">Статус</div>
    <FieldsTable :pairs="[
      ['Активна', account.enabled], ['Тип УЗ', account.account_type],
      ['Заблокирована', account.locked_out],
      ['Время блокировки', account.account_lockout_time],
    ]" />
    <div class="ucard-ad-section-label">Пароль</div>
    <FieldsTable :pairs="[
      ['Смена пароля', account.password_last_set], ['Пароль сменён', account.pwd_last_set],
      ['Треб. смена пароля', account.must_change_password],
      ['Пароль просрочен', account.password_expired],
      ['Бессрочный пароль', account.password_never_expires],
      ['Пароль не требуется', account.password_not_required],
      ['Запрет смены пароля', account.cannot_change_password],
    ]" />
    <div class="ucard-ad-section-label">Срок действия</div>
    <FieldsTable :pairs="[
      ['Срок УЗ', account.account_expires], ['Дата окончания', account.account_expiration_date],
    ]" />
    <div class="ucard-ad-section-label">Активность</div>
    <FieldsTable :pairs="[
      ['Последний вход', account.last_logon_date],
      ['Посл. вход (timestamp)', account.last_logon_timestamp],
      ['Кол-во входов', account.logon_count],
      ['Посл. ошибка пароля', account.last_bad_password_attempt],
      ['Кол-во ошибок', account.bad_logon_count],
    ]" />
    <div class="ucard-ad-section-label">Жизненный цикл</div>
    <FieldsTable :pairs="[
      ['Создана', account.created_date], ['Изменена', account.modified_date],
      ['whenCreated', account.when_created], ['whenChanged', account.when_changed],
      ['Дата выгрузки', account.exported_at],
    ]" />
    <div class="ucard-ad-section-label">Безопасность</div>
    <FieldsTable :pairs="[
      ['Делегирование', account.trusted_for_delegation],
      ['Протокольный переход', account.trusted_to_auth_for_delegation],
      ['Запрет делегирования', account.account_not_delegated],
      ['Без Kerberos Pre-Auth', account.does_not_require_preauth],
      ['Обратимое шифрование', account.allow_reversible_password_encryption],
      ['Только смарт-карта', account.smartcard_logon_required],
      ['Защита от удаления', account.protected_from_accidental_deletion],
      ['UAC', account.user_account_control],
      ['SPN', account.service_principal_names],
    ]" />
    <div class="ucard-ad-section-label">Идентификаторы</div>
    <FieldsTable :pairs="[
      ['ObjectGUID', account.object_guid], ['SID', account.sid],
      ['CanonicalName', account.canonical_name],
      ['DN', account.distinguished_name],
      ['StaffUUID', account.staff_uuid],
    ]" />
    <div class="ucard-ad-section-label">Профиль</div>
    <FieldsTable :pairs="[
      ['Рабочие станции', account.logon_workstations],
      ['Диск', account.home_drive], ['Дом. каталог', account.home_directory],
      ['Профиль', account.profile_path], ['Скрипт', account.script_path],
    ]" />
    <div class="ucard-ad-section-label">Связи</div>
    <FieldsTable :pairs="[
      ['Группы', { html: groupsHtml(account.groups) }],
      ['Подчинённые', { html: dnLinksHtml(account.direct_reports) }],
      ['Управляемые объекты', { html: dnLinksHtml(account.managed_objects) }],
      ['Основная группа', { html: dnLinksHtml(account.primary_group) }],
    ]" />
    <template v-if="account.info">
      <div class="ucard-ad-section-label">Прочее</div>
      <FieldsTable :pairs="[['Инфо', account.info]]" />
    </template>
  </div>
</template>
