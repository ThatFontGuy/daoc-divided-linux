using DOL.Database.Attributes;

namespace DOL.Database
{
    /// <summary>
    /// Which item a GameCustomCurrencyMerchant takes as payment, per merchant item list.
    /// Item prices on that list are counts of the currency item (like Darkness Falls seals).
    /// </summary>
    [DataTable(TableName = "offline_currency_lists")]
    public class DbOfflineCurrencyList : DataObject
    {
        private string _itemListId = string.Empty;
        private string _currencyItem = string.Empty;
        private string _description;

        [PrimaryKey]
        public string ItemListID
        {
            get => _itemListId;
            set { Dirty = true; _itemListId = value; }
        }

        /// <summary>ItemTemplate.Id_nb of the item paid to the merchant.</summary>
        [DataElement(AllowDbNull = false, Varchar = 255)]
        public string CurrencyItem
        {
            get => _currencyItem;
            set { Dirty = true; _currencyItem = value; }
        }

        [DataElement(AllowDbNull = true)]
        public string Description
        {
            get => _description;
            set { Dirty = true; _description = value; }
        }
    }
}
