import { t } from 'i18next';

export const formatCurrency = (amount) => {
  return new Intl.NumberFormat('uz-UZ', {
    style: 'currency',
    currency: 'UZS'
  }).format(amount);
};

export const formatDate = (date) => {
  return new Intl.DateTimeFormat('uz-UZ').format(new Date(date));
};